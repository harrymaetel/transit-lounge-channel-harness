import importlib.util
from pathlib import Path
import unittest
import copy
import json

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "harness.py"
SPEC = importlib.util.spec_from_file_location("transit_harness", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_job():
    return {
        "schema_version": "1.0", "job_id": "event-01", "channel": "instagram",
        "category": "event", "state": "user_approved", "objective": "방문",
        "audience": "예비 방문자", "message": "행사 정보를 확인하세요",
        "source_ids": ["s1"], "sources": [{"id": "s1", "checked": True}],
        "approvals": {"content": True, "design": True, "publish": True},
        "qa": {"structural": True, "content": True, "visual": True, "release": True},
    }


class HarnessTests(unittest.TestCase):
    def test_valid_job(self):
        self.assertEqual(MODULE.validate(valid_job()), [])

    def test_other_category_uses_jev(self):
        job = valid_job()
        job["category"] = "other"
        self.assertTrue(MODULE.route(job)["use_jev"])

    def test_category_rule_is_conditionally_loaded(self):
        self.assertIn("subskills/categories/event.md", MODULE.route(valid_job())["load_sequence"])

    def test_ready_does_not_authorize_external_publish(self):
        result = MODULE.readiness(valid_job())
        self.assertTrue(result["ready"])
        self.assertFalse(result["external_publish_authorized"])

    def test_agent_cards_are_short(self):
        self.assertEqual(MODULE.validate_cards(), [])

    def test_decision_contract(self):
        entry = {"id": "2026-10-29-v0.1", "status": "H", "target": "event", "choice": "4장", "why": "사용자 선택"}
        self.assertEqual(MODULE.validate_decision(entry), [])


def sample(name="event"):
    return json.loads((SCRIPT.parents[1] / "examples" / f"{name}-job.json").read_text())


def rendered_editorial():
    job = valid_job()
    job.update(schema_version="1.1", state="design_ready")
    job["deliverables"] = [{"kind": "carousel", "cards": 1}]
    job["pages"] = [{
        "id": "p01", "role": "Story-Quote", "pattern": "editorial",
        "content": {"title": "기록을 나누는 시간", "body": "함께 기록을 나눠요.", "support": "편집부"},
        "render": {
            "node_id": "frame-1", "inspected_at": "test-fixture", "evidence": "synthetic-test-only",
            "layout": "title-body-support", "overflow": False,
            "font_runs": [{"family": "Neulis Alt", "style": "Regular"},
                          {"family": "Neulis Alt", "style": "Bold"},
                          {"family": "Neulis Alt", "style": "Medium"}],
            "slots": {
                "title": {"node_id": "t1", "lines": 1, "family": "Neulis Alt", "style": "Bold", "overflow": False},
                "body": {"node_id": "t2", "lines": 1, "family": "Neulis Alt", "style": "Medium", "overflow": False},
                "support": {"node_id": "t3", "lines": 1, "family": "Neulis Alt", "style": "Medium", "overflow": False},
            },
        },
    }]
    return job


class PageContractTests(unittest.TestCase):
    def test_examples_validate_but_are_not_ready(self):
        for name in ("event", "playlist"):
            job = sample(name)
            self.assertEqual(MODULE.validate(job), [])
            self.assertFalse(MODULE.readiness(job)["ready"])

    def test_six_category_routes_and_refs_exist(self):
        for category, count in (("event", 6), ("playlist", 5), ("link-mingle", 8),
                                ("interview", 5), ("moments", 4), ("lines", 4)):
            job = valid_job()
            job["category"] = category
            result = MODULE.route(job)
            self.assertEqual(len(result["page_templates"]), count)
            self.assertFalse(result["page_count_is_limit"])
            for path in result["load_sequence"]:
                self.assertTrue((SCRIPT.parents[1] / path).is_file(), path)

    def test_flat_list_cannot_replace_structured_items(self):
        job = sample()
        job["pages"][3]["items"] = ["기록하는 분", "새로 시작하는 분"]
        self.assertTrue(any("structured-audience-pill" in e for e in MODULE.validate(job)))

    def test_four_items_require_additional_page(self):
        job = sample()
        job["pages"][3]["items"] *= 2
        self.assertTrue(any("split-page-at-3" in e for e in MODULE.validate(job)))

    def test_more_than_six_pages_allowed_and_program_numbers_continue(self):
        job = sample()
        page = copy.deepcopy(job["pages"][4])
        page["id"] = "p05b"
        page["items"] = [{"kind": "program-pill", "order": 4, "text": "기록 돌아보기"}]
        job["pages"].insert(5, page)
        job["deliverables"][0]["cards"] = 7
        self.assertEqual(MODULE.validate(job), [])
        page["items"][0]["order"] = 1
        self.assertIn("pages:program-order-must-continue-across-pages", MODULE.validate(job))

    def test_track_artwork_is_required(self):
        job = sample("playlist")
        del job["pages"][2]["items"][0]["artwork_ref"]
        self.assertTrue(any("artwork_ref:required" in e for e in MODULE.validate(job)))

    def test_track_support_requires_room_or_another_page(self):
        job = sample("playlist")
        page = job["pages"][2]
        page["content"]["support"] = "이어지는 음악도 들어보세요"
        self.assertTrue(any("content-height-896>860" in e for e in MODULE.validate(job)))
        page["items"].pop()
        self.assertEqual(MODULE.validate(job), [])

    def test_unicode_spaces_and_blank_lines(self):
        self.assertEqual(MODULE.text_metrics("가 나\r\n\r\n다!"), (5, 3))

    def test_program_number_consumes_character_budget(self):
        job = sample()
        job["pages"][4]["items"][0]["text"] = "가" * 17
        self.assertTrue(any("chars-21>20" in e for e in MODULE.validate(job)))

    def test_design_requires_render_not_just_copy(self):
        job = sample()
        job["state"] = "design_ready"
        self.assertTrue(any("render:required" in e for e in MODULE.validate(job)))

    def test_font_substitution_fails(self):
        job = rendered_editorial()
        self.assertEqual(MODULE.validate(job), [])
        job["pages"][0]["render"]["font_runs"][0]["family"] = "Pretendard"
        self.assertTrue(any("neulis-alt-required" in e for e in MODULE.validate(job)))

    def test_title_must_be_bold_and_separate(self):
        job = rendered_editorial()
        slots = job["pages"][0]["render"]["slots"]
        slots["title"]["style"] = "Medium"
        slots["body"]["node_id"] = slots["title"]["node_id"]
        errors = MODULE.validate(job)
        self.assertTrue(any("role-font-mismatch" in e for e in errors))
        self.assertTrue(any("separate-text-node-required" in e for e in errors))

    def test_automatic_wrap_is_checked_separately(self):
        job = rendered_editorial()
        job["pages"][0]["render"]["slots"]["title"]["lines"] = 3
        self.assertTrue(any("rendered-line-limit" in e for e in MODULE.validate(job)))

    def test_combined_height_is_checked_even_when_each_slot_fits(self):
        job = rendered_editorial()
        slots = job["pages"][0]["render"]["slots"]
        slots["title"]["lines"] = 2
        slots["body"]["lines"] = 9
        self.assertTrue(any("content-height-932>860" in e for e in MODULE.validate(job)))

    def test_ready_requires_font_and_element_review(self):
        job = rendered_editorial()
        job["state"] = "user_approved"
        self.assertFalse(MODULE.readiness(job)["ready"])
        job["qa"].update(typography=True, element_layout=True)
        self.assertFalse(MODULE.readiness(job)["ready"])
        self.assertFalse(MODULE.readiness(job)["gates"]["current_render_contract"])



if __name__ == "__main__":
    unittest.main()

