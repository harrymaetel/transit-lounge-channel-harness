#!/usr/bin/env python3
"""Deterministic routing and release checks for Transit Lounge channel work."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

STATES = [
    "draft", "classified", "strategy_ready", "copy_ready", "design_ready",
    "qa_passed", "user_approved", "publish_ready", "published", "analyzed", "leveled_up",
]
CATEGORIES = {"event", "playlist", "link-mingle", "interview", "moments", "lines", "other"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


def catalog() -> dict:
    return read_json(str(ROOT / "references" / "pattern-catalog.json"))


def is_carousel(job: dict) -> bool:
    return bool(job.get("pages")) or any(
        isinstance(d, dict) and d.get("kind") == "carousel"
        for d in job.get("deliverables", [])
    )


def text_metrics(text: str) -> tuple[int, int]:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return len(text.replace("\n", "")), len(text.split("\n"))


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def bounds(value):
    return (isinstance(value, dict) and all(finite(value.get(k)) for k in ("x", "y", "width", "height"))
            and value["width"] > 0 and value["height"] > 0)


def contains(outer, inner, tolerance=0.5):
    return (bounds(outer) and bounds(inner) and inner["x"] >= outer["x"] - tolerance
            and inner["y"] >= outer["y"] - tolerance
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance)


def overlaps(a, b):
    return (bounds(a) and bounds(b) and a["x"] < b["x"] + b["width"] - 0.5
            and b["x"] < a["x"] + a["width"] - 0.5
            and a["y"] < b["y"] + b["height"] - 0.5
            and b["y"] < a["y"] + a["height"] - 0.5)


def validate_render_evidence(page, render, texts, rules, category):
    """v1.2: verify measured geometry and complete text inventory, not just PASS flags."""
    errors = []
    canvas = render.get("canvas", {})
    expected = dict(x=0, y=0, **rules["canvas"])
    if not bounds(canvas) or any(canvas.get(k) != v for k, v in expected.items()):
        errors.append("canvas:expected-1080x1350")
    font_check = render.get("font_check", {})
    if not isinstance(font_check, dict):
        font_check = {}
    if (font_check.get("environment") not in ("figma-desktop", "figma-remote")
            or font_check.get("loaded_styles") != rules["font_styles"]
            or font_check.get("missing_fonts") is not False or not font_check.get("evidence")):
        errors.append("font-check:loaded-neulis-evidence-required")
    inventory = render.get("text_nodes")
    if not isinstance(inventory, list) or not inventory:
        return errors + ["text-inventory:required"]
    if type(render.get("text_node_count")) is not int or render["text_node_count"] != len(inventory):
        errors.append("text-inventory:count-mismatch")
    nodes = {}
    for n in inventory:
        if not isinstance(n, dict) or not isinstance(n.get("node_id"), str) or not n["node_id"]:
            errors.append("text-inventory:invalid-node")
            continue
        nid = n["node_id"]
        if nid in nodes:
            errors.append("text-inventory:duplicate-node")
        nodes[nid] = n
        if n.get("effective_visible") is not True or n.get("missing_font") is not False:
            errors.append(f"{nid}:hidden-or-missing-font")
        if n.get("clipped") is not False or not contains(expected, n.get("bounds")):
            errors.append(f"{nid}:clipped-or-outside-canvas")
        runs = n.get("font_runs", [])
        if (not isinstance(runs, list) or not runs
                or any(not isinstance(r, dict) or r.get("family") != "Neulis Alt"
                       or r.get("style") not in rules["font_styles"] for r in runs)):
            errors.append(f"{nid}:neulis-alt-required")
    reported = render.get("slots", {})
    if not isinstance(reported, dict):
        reported = {}
    slot_nodes = []
    for key, (value, limit) in texts.items():
        report = reported.get(key, {})
        nid = report.get("node_id") if isinstance(report, dict) else None
        n = nodes.get(nid) if isinstance(nid, str) else None
        if not n:
            errors.append(f"{key}:missing-measured-node")
            continue
        slot_nodes.append(n)
        normalize = lambda s: unicodedata.normalize("NFC", s.replace("\r\n", "\n").replace("\r", "\n"))
        if not isinstance(n.get("text"), str) or normalize(n["text"]) != normalize(value):
            errors.append(f"{key}:rendered-copy-mismatch")
        if n.get("auto_resize") != "HEIGHT" or n.get("paragraph_spacing") != 0:
            errors.append(f"{key}:auto-height-zero-paragraph-spacing-required")
        runs = n.get("font_runs", [])
        b = n.get("bounds", {})
        lh = limit.get("line_height_percent", 150) * limit["font_size"] / 100
        if (not isinstance(runs, list) or not runs or any(not isinstance(r, dict)
                or r.get("family") != "Neulis Alt" or r.get("style") != limit["font_style"]
                or r.get("font_size") != limit["font_size"]
                or not finite(r.get("line_height_px")) or abs(r["line_height_px"] - lh) > 0.02 for r in runs)):
            errors.append(f"{key}:measured-role-typography-mismatch")
        if bounds(b):
            count = round(b["height"] / lh)
            if (count < text_metrics(value)[1] or count > limit["max_lines"]
                    or abs(b["height"] - count * lh) > 1.1 or report.get("lines") != count):
                errors.append(f"{key}:measured-line-count-mismatch")
    header = render.get("header", {})
    if not isinstance(header, dict):
        header = {}
    header_ids = [header.get("brand_node_id"), header.get("category_node_id")]
    if len(set(str(x) for x in header_ids)) != 2:
        errors.append("header:distinct-brand-and-category-required")
    for nid, label in zip(header_ids, ["Transit", rules["category_labels"].get(category)]):
        n = nodes.get(nid) if isinstance(nid, str) else None
        if not n or n.get("text") != label or n.get("effective_visible") is not True:
            errors.append("header:missing-or-wrong-label")
    logo = render.get("logo", {})
    if not isinstance(logo, dict):
        logo = {}
    if (not logo.get("node_id") or logo.get("effective_visible") is not True
            or not contains(expected, logo.get("bounds"))):
        errors.append("logo:missing-or-outside-canvas")
    for n in slot_nodes:
        if overlaps(n.get("bounds"), logo.get("bounds")):
            errors.append("layout:text-overlaps-logo")
    # Full-width text boxes may overlap horizontally; only vertical overlap with
    # another content slot is a collision. Header/cover exceptions are separate.
    for i, a in enumerate(slot_nodes):
        for b in slot_nodes[i + 1:]:
            if overlaps(a.get("bounds"), b.get("bounds")):
                errors.append("layout:content-slots-overlap")
    spec = rules["patterns"][page["pattern"]]
    ordered = [reported.get(k, {}).get("node_id") for k in ("eyebrow", "title", "body", "support")
               if k in texts and isinstance(reported.get(k), dict)]
    ordered = [nodes[n] for n in ordered if isinstance(n, str) and n in nodes and bounds(nodes[n].get("bounds"))]
    if any(a["bounds"]["y"] >= b["bounds"]["y"] for a, b in zip(ordered, ordered[1:])):
        errors.append("layout:title-body-support-order")
    if "content_height_budget" in spec:
        box = render.get("content_bounds")
        if not contains(expected, box) or box["height"] > spec["content_height_budget"]:
            errors.append("layout:measured-content-height-or-bounds")
        elif any(not contains(box, n.get("bounds")) for n in slot_nodes):
            errors.append("layout:content-outside-container")
    if page.get("poster_content"):
        box = render.get("poster_bounds")
        if (not contains(expected, box) or box["width"] != 700 or box["height"] != 937
                or render.get("poster_size_mode") != "FIXED"):
            errors.append("poster:fixed-700x937-required")
    row_boxes = []
    elements = render.get("elements", [])
    for index, e in enumerate(elements if isinstance(elements, list) else []):
        if not isinstance(e, dict):
            continue
        ir = spec.get("items", {})
        box = e.get("bounds")
        if not contains(expected, box) or box["height"] != ir.get("row_height"):
            errors.append("element:measured-row-bounds")
        if e.get("effective_visible") is not True:
            errors.append("element:hidden-container")
        if bounds(box):
            if row_boxes and box["y"] < row_boxes[-1]["y"] + row_boxes[-1]["height"]:
                errors.append("element:row-order-or-overlap")
            row_boxes.append(box)
            for key in texts:
                if not key.startswith(f"items.{index}."):
                    continue
                report = reported.get(key, {})
                nid = report.get("node_id") if isinstance(report, dict) else None
                n = nodes.get(nid) if isinstance(nid, str) else None
                if not n or not contains(box, n.get("bounds")):
                    errors.append("element:text-outside-own-row")
            for key in ("eyebrow", "title", "support"):
                report = reported.get(key, {})
                nid = report.get("node_id") if isinstance(report, dict) else None
                n = nodes.get(nid) if isinstance(nid, str) else None
                if key in texts and n and bounds(n.get("bounds")):
                    b = n["bounds"]
                    if (key == "support" and b["y"] < box["y"] + box["height"]
                            or key != "support" and b["y"] + b["height"] > box["y"]):
                        errors.append("element:title-rows-support-order")
        if e.get("kind") == "track-row" and (not e.get("artwork_node_id") or e.get("artwork_visible") is not True):
            errors.append("element:visible-artwork-required")
    visual = render.get("visual_review", {})
    if not isinstance(visual, dict):
        visual = {}
    if not visual.get("evidence") or any(visual.get(k) is not True for k in ("contrast", "faces_clear", "asset_matches_copy", "logo_clear")):
        errors.append("visual:review-evidence-required")
    return errors


def validate_pages(job: dict) -> list[str]:
    """Check copy budgets and reported render evidence, not the canvas itself."""
    errors = []
    state = job.get("state")
    rank = STATES.index(state) if state in STATES else -1
    pages = job.get("pages")
    if pages is None:
        if is_carousel(job) and rank >= STATES.index("copy_ready"):
            errors.append("pages:required-from-copy_ready")
        return errors
    if not isinstance(pages, list) or not pages:
        return ["pages:must-be-nonempty-array"]
    rules = catalog()
    allowed = {p["pattern"] for p in rules["categories"].get(job.get("category"), [])}
    render_required = rank >= STATES.index("design_ready")
    page_ids, program_orders = set(), []
    for i, page in enumerate(pages):
        prefix = f"pages[{i}]"
        if not isinstance(page, dict):
            errors.append(f"{prefix}:must-be-object")
            continue
        pid = page.get("id")
        if not isinstance(pid, str) or not pid or pid in page_ids:
            errors.append(f"{prefix}:missing-or-duplicate-id")
        else:
            page_ids.add(pid)
        pattern = page.get("pattern")
        spec = rules["patterns"].get(pattern) if isinstance(pattern, str) else None
        if not spec or pattern not in allowed:
            errors.append(f"{prefix}:unsupported-category-pattern")
            continue
        content = page.get("content", {})
        if not isinstance(content, dict):
            errors.append(f"{prefix}.content:must-be-object")
            continue
        if set(content) - set(spec["slots"]):
            errors.append(f"{prefix}.content:unknown-slot")
        texts = {}
        for key, limit in spec["slots"].items():
            value = content.get(key, "")
            if not isinstance(value, str):
                errors.append(f"{prefix}.{key}:must-be-text")
            elif not value.strip():
                if limit["required"]:
                    errors.append(f"{prefix}.{key}:required")
            else:
                texts[key] = (value, limit)
        if "poster_content" in page and job.get("schema_version") == "1.2":
            poster = page["poster_content"]
            artwork = spec.get("artwork_slots", {})
            if not isinstance(poster, dict) or not artwork or set(poster) != set(artwork):
                errors.append(f"{prefix}.poster_content:invalid-slots")
            else:
                for key, limit in artwork.items():
                    value = poster[key]
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"{prefix}.artwork.{key}:required-text")
                    else:
                        texts[f"artwork.{key}"] = (value, limit)
        if spec.get("asset_required") and not page.get("asset_ref"):
            errors.append(f"{prefix}.asset_ref:required")
        item_rule = spec.get("items")
        items = page.get("items", [])
        if not isinstance(items, list):
            errors.append(f"{prefix}.items:must-be-array")
            items = []
        if item_rule:
            if not item_rule["min"] <= len(items) <= item_rule["max"]:
                errors.append(f"{prefix}.items:split-page-at-{item_rule['max']}")
            for j, item in enumerate(items):
                ip = f"{prefix}.items[{j}]"
                if not isinstance(item, dict) or item.get("kind") != item_rule["kind"]:
                    errors.append(f"{ip}:structured-{item_rule['kind']}-required")
                    continue
                if item_rule.get("artwork_required") and not item.get("artwork_ref"):
                    errors.append(f"{ip}.artwork_ref:required")
                order = item.get("order")
                if item_rule.get("order_required"):
                    if type(order) is not int or order < 1:
                        errors.append(f"{ip}.order:positive-integer-required")
                    else:
                        program_orders.append(order)
                for field, limit in item_rule["fields"].items():
                    value = item.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"{ip}.{field}:required-text")
                    else:
                        if field == "text" and item_rule.get("order_required") and type(order) is int:
                            value = f"{order:02d}  {value}"
                        texts[f"items.{j}.{field}"] = (value, limit)
        elif items:
            errors.append(f"{prefix}.items:not-supported")
        for key, (value, limit) in texts.items():
            chars, lines = text_metrics(value)
            if chars > limit["max_chars"]:
                errors.append(f"{prefix}.{key}:chars-{chars}>{limit['max_chars']}")
            if lines > limit["max_lines"]:
                errors.append(f"{prefix}.{key}:lines-{lines}>{limit['max_lines']}")
        render = page.get("render")
        if render_required and not isinstance(render, dict):
            errors.append(f"{prefix}.render:required-from-design_ready")
        measured = {}
        if isinstance(render, dict):
            if not all(render.get(k) for k in ("node_id", "inspected_at", "evidence")):
                errors.append(f"{prefix}.render:missing-evidence")
            if render.get("layout") != spec["layout"]:
                errors.append(f"{prefix}.render:layout-mismatch")
            if render.get("overflow") is not False:
                errors.append(f"{prefix}.render:overflow-or-unchecked")
            runs = render.get("font_runs")
            if not isinstance(runs, list) or not runs:
                errors.append(f"{prefix}.render:font-runs-required")
                runs = []
            if any(not isinstance(r, dict) or r.get("family") != "Neulis Alt"
                   or r.get("style") not in rules["font_styles"] for r in runs):
                errors.append(f"{prefix}.render:neulis-alt-required")
            observed = render.get("slots", {})
            if not isinstance(observed, dict):
                observed = {}
            node_ids = set()
            for key, (_, limit) in texts.items():
                report = observed.get(key, {})
                if not isinstance(report, dict):
                    report = {}
                node = report.get("node_id")
                if not isinstance(node, str) or not node or node in node_ids:
                    errors.append(f"{prefix}.{key}:separate-text-node-required")
                else:
                    node_ids.add(node)
                count = report.get("lines")
                if type(count) is not int or count < 1 or count > limit["max_lines"]:
                    errors.append(f"{prefix}.{key}:rendered-line-limit-or-unchecked")
                else:
                    measured[key] = count
                if report.get("family") != "Neulis Alt" or report.get("style") != limit["font_style"]:
                    errors.append(f"{prefix}.{key}:role-font-mismatch")
                if report.get("overflow") is not False:
                    errors.append(f"{prefix}.{key}:overflow-or-unchecked")
            if item_rule:
                elements = render.get("elements", [])
                if (not isinstance(elements, list) or len(elements) != len(items)
                    or any(not isinstance(e, dict) or e.get("kind") != item_rule["kind"]
                           or not isinstance(e.get("container_node_id"), str) or not e["container_node_id"]
                           for e in elements)):
                    errors.append(f"{prefix}.render:separate-item-containers-required")
                elif len({e["container_node_id"] for e in elements}) != len(elements):
                    errors.append(f"{prefix}.render:duplicate-item-container")
            if job.get("schema_version") == "1.2":
                errors.extend(f"{prefix}.{e}" for e in validate_render_evidence(page, render, texts, rules, job.get("category")))
        if "content_height_budget" in spec:
            if item_rule:
                height = sum((measured.get(k) or text_metrics(v)[1]) * lim["font_size"] * 1.5
                             for k, (v, lim) in texts.items() if not k.startswith("items."))
                height += spec["eyebrow_title_gap"] + spec["block_gap"]
                height += len(items) * item_rule["row_height"] + max(0, len(items) - 1) * item_rule["row_gap"]
                if "support" in texts:
                    height += spec["block_gap"]
            else:
                height = sum((measured.get(k) or text_metrics(v)[1]) * lim["font_size"] * 1.5
                             for k, (v, lim) in texts.items()) + 40 * max(0, len(texts) - 1)
            if height > spec["content_height_budget"]:
                errors.append(f"{prefix}:content-height-{height:g}>{spec['content_height_budget']}")
    if program_orders and program_orders != list(range(1, len(program_orders) + 1)):
        errors.append("pages:program-order-must-continue-across-pages")
    for d in job.get("deliverables", []):
        if isinstance(d, dict) and d.get("kind") == "carousel" and d.get("cards") != len(pages):
            errors.append("deliverables.cards:must-match-pages")
    return errors


def read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def validate(job: dict) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "job_id", "channel", "category", "state", "objective", "audience", "message"]
    for key in required:
        if not job.get(key):
            errors.append(f"missing:{key}")
    if job.get("schema_version") not in {"1.0", "1.1", "1.2"}:
        errors.append("schema_version:expected-1.0-or-1.1-or-1.2")
    if job.get("job_id") and not SLUG.match(str(job["job_id"])):
        errors.append("job_id:invalid-slug")
    if job.get("category") not in CATEGORIES:
        errors.append("category:unsupported")
    if job.get("state") not in STATES:
        errors.append("state:unsupported")
    sources = job.get("sources", [])
    source_ids = job.get("source_ids", [])
    ids = {s.get("id") for s in sources if isinstance(s, dict)}
    if not source_ids:
        errors.append("source_ids:empty")
    if any(sid not in ids for sid in source_ids):
        errors.append("source_ids:unknown")
    for name in ("approvals", "qa"):
        if not isinstance(job.get(name, {}), dict):
            errors.append(f"{name}:must-be-object")
    errors.extend(validate_pages(job))
    return errors


def route(job: dict) -> dict:
    category = job.get("category", "other")
    ambiguous = category == "other" or not job.get("objective") or not job.get("message")
    sequence = [
        "agents/brand.md", "subskills/brand-governance.md",
        "agents/strategy.md", "subskills/content-strategy.md",
    ]
    if job.get("research_required"):
        sequence[2:2] = ["agents/scout.md", "subskills/scout-research.md"]
    sequence += [
        "agents/copy.md", "subskills/copy-production.md",
        "references/page-patterns.md", "references/pattern-catalog.json",
        "agents/design.md", "subskills/design-routing.md", "references/design-system.md",
        "references/font-workflow.md",
        "references/figma-production.md", "references/render-evidence.md",
        "agents/qa.md", "subskills/qa-release.md",
    ]
    if category != "other":
        sequence.insert(sequence.index("agents/copy.md"), f"subskills/categories/{category}.md")
    if ambiguous:
        sequence[0:0] = ["agents/jev.md", "subskills/jev-routing.md"]
    if category in {"event", "playlist"}:
        sequence.insert(sequence.index("agents/qa.md"), "references/element-patterns.md")
    rules = catalog()
    return {"category": category, "use_jev": ambiguous, "load_sequence": sequence,
            "page_templates": rules["categories"].get(category, []),
            "page_count_is_limit": False, "font_family": rules["font_family"]}


def readiness(job: dict) -> dict:
    errors = validate(job)
    approvals = job.get("approvals", {})
    qa = job.get("qa", {})
    gates = {
        "sources_checked": bool(job.get("source_ids")) and all(s.get("checked") for s in job.get("sources", [])),
        "content_approved": approvals.get("content") is True,
        "design_approved": approvals.get("design") is True,
        "publish_approved": approvals.get("publish") is True,
        "structural_qa": qa.get("structural") is True,
        "content_qa": qa.get("content") is True,
        "visual_qa": qa.get("visual") is True,
        "release_qa": qa.get("release") is True,
    }
    if is_carousel(job):
        gates["current_render_contract"] = job.get("schema_version") == "1.2"
        gates["typography_qa"] = qa.get("typography") is True
        gates["element_layout_qa"] = qa.get("element_layout") is True
    state = job.get("state")
    advanced = state in STATES and STATES.index(state) >= STATES.index("user_approved")
    ready = not errors and all(gates.values()) and advanced
    return {"ready": ready, "external_publish_authorized": False, "errors": errors, "gates": gates}


def validate_cards() -> list[str]:
    errors: list[str] = []
    for path in sorted(AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if len(text) > 300:
            errors.append(f"agent-card-too-long:{path.name}:{len(text)}")
    return errors


def validate_decision(entry: dict) -> list[str]:
    errors: list[str] = []
    if set(entry) != {"id", "status", "target", "choice", "why"}:
        errors.append("decision:expected-id-status-target-choice-why")
    if entry.get("status") not in {"H", "P"}:
        errors.append("decision:status-must-be-H-or-P")
    if any(not isinstance(entry.get(k), str) or not entry.get(k, "").strip() for k in ("id", "target", "choice", "why")):
        errors.append("decision:fields-must-be-nonempty-strings")
    encoded = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > 240:
        errors.append(f"decision:too-long:{len(encoded)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "route", "check-ready"):
        command = sub.add_parser(name)
        command.add_argument("--job", required=True)
    sub.add_parser("validate-cards")
    decision = sub.add_parser("log-decision")
    decision.add_argument("--entry", required=True, help="JSON object string")
    decision.add_argument("--log", default=str(ROOT / "decision-log.jsonl"))
    args = parser.parse_args()
    if args.command == "validate-cards":
        errors = validate_cards()
        result = {"ok": not errors, "errors": errors}
    elif args.command == "log-decision":
        entry = json.loads(args.entry)
        errors = validate_decision(entry)
        if not errors:
            with open(args.log, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        result = {"ok": not errors, "errors": errors, "written": not errors}
    else:
        job = read_json(args.job)
        if args.command == "validate":
            errors = validate(job)
            result = {"ok": not errors, "errors": errors}
        elif args.command == "route":
            result = route(job)
        else:
            result = readiness(job)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", result.get("ready", True)) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)

