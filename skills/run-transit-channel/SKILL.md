---
name: run-transit-channel
description: Plan, produce, review, and improve Transit Lounge channel content while preserving its approved brand, category system, release gates, and human approval boundaries.
---

# Run Transit Channel

Use this skill for Transit Lounge channel planning, copy, design, QA, publishing preparation, performance review, or Levelup proposals.

1. Read `../../AGENTS.md` and `../../harness/brand-core.md`.
2. For a new content request, follow [콘텐츠 제작 접수](../../harness/subskills/content-intake.md) before creating the job. Reuse the saved brief and update changed answers or photos on follow-up. Create a job using `../../harness/references/job-schema.md` (new carousel jobs use schema 1.2).
3. Run `python3 ../../harness/scripts/harness.py route --job <job.json>` from this skill directory, then read the returned `load_sequence` relative to `../../harness/`. Use `page_templates` as an extensible sequence, not a fixed page count.
4. Keep planning, production, visual QA, user approval, and external publishing as separate gates.
5. Use Jev only for ambiguity, conflicting QA, or retrospective hypothesis selection. If unavailable, continue with local rules and human review.
6. Apply `humanize-korean` to final Korean copy without changing facts, numbers, names, quotations, or intent.
7. Before handoff, run `validate` and `check-ready`. Never treat `ready` as authorization to publish or modify an external account.

On a new workstation, follow the [font setup workflow](../../harness/references/font-workflow.md). Run the read-only check on the target workstation and offer opt-in setup for missing styles.

Keep Neulis Alt, including Regular/Medium/Bold roles. Check the execution environment before editing text; if the connector cannot load it, use Figma desktop. Never substitute Pretendard or another family automatically. Follow `../../harness/references/font-workflow.md`.

For each page, separate the content title, main content and supporting copy. Keep the brand header and logo distinct. Audience pills, numbered program pills and single-track pages with the album cover above the title and credits are structured elements, never a multiline paragraph. Load `../../harness/references/page-patterns.md` and the selected category rule; exact operational limits and element contracts come from `../../harness/references/pattern-catalog.json`. Read `../../harness/references/element-patterns.md` when using repeated elements. The 2026-10-30 observed layouts and still-unconverted legacy examples are distinguished in the pattern guide.

Before Figma production, load `../../harness/references/figma-production.md`. After composition, use the measured evidence contract in `../../harness/references/render-evidence.md`; fixed text height, hidden ancestors, missing headers, and stale screenshots cannot pass. The reusable helpers in `../../harness/scripts/figma_helpers.js` run in the native desktop Plugin API and must not be confused with MCP-only convenience APIs. Keep historical run scripts out of new production.
