# reelmetric-design-system

Canonical public design-system source for ReelMetrics, per
[ADR-0054](https://github.com/king44444/reelmetrics/blob/main/docs/internal/planning/decisions/ADR-0054_public_design_system_source_and_delivery.md)
(Accepted — signed by Mike King 2026-08-30 and Cheryl King 2026-08-31). One layered
CSS source compiles to three delivery outputs: linked CSS for `reelmetric-script-web`,
linked CSS for `reelmetric-landing`, and an embedded Python string for
`reelmetric-script-pipeline`'s offline/CLI report generator.

**Status: T152.02 (stand up this repo) is done. No consumer is wired yet.** That is
T152.03 (`reelmetric-script-web`) and T152.04 (`reelmetric-landing`), tracked in the
workspace [`WORK_QUEUE.md`](https://github.com/king44444/reelmetrics/blob/main/WORK_QUEUE.md).
This README does not claim anything beyond what is actually built in this repo.

## Layers

```css
@layer reset, tokens, base, components, report, utilities, overrides;
```

| File | Layer(s) it fills | Content |
|---|---|---|
| `src/tokens.css` | `tokens` | Design tokens (`:root` custom properties) — seeded verbatim from `reelmetric-script-web`'s theme file as it stood after T151.10's monochrome redesign |
| `src/base.css` | `reset`, `base` | Box-sizing reset, page/section primitives, heading/typography rules |
| `src/components.css` | `components`, `utilities` | Buttons, nav, hero, cards, tables, tags, CTA, footer, plus the responsive and reduced-motion rules |
| `src/report.css` | `report` | Placeholder. `report_user.html`, `decision_package.html`, and `worksheet_public.html` keep their template-local `<style>` blocks until a later extraction phase — this task does not touch them |
| `src/overrides/bootstrap.css` | `overrides` | Bootstrap CDN override surface (ADR-0054 SS3 keeps the Bootstrap CDN link in consuming templates). Empty until a consumer needs an actual override — an empty layer is valid CSS |

## Build

Python only. No `package.json`, no `node_modules`, no npm invocation anywhere in this
repo or its CI (ADR-0054 SS2.3) — `scripts/check_no_js_toolchain.sh` and a repo-wide test
both assert this.

```bash
make build   # -> dist/reelmetrics-public.css
             #    dist/reelmetrics_design_system.py   (EMBEDDED_CSS string)
             #    dist/reelmetrics-design-system.lock  (the 5 fields ADR-0054 SS2.5 names)
             #    dist/CHECKSUMS.txt
make test    # pytest — reproducibility, layer completeness, lock fields, no-JS guard
```

`make build` run twice with no source change produces byte-identical output. That
determinism is what a consumer's drift check relies on (ADR-0054 SS2.5): fetch this
repo at the lock's committed SHA, rebuild, and compare the rebuilt output against the
committed one — proving the pinned SHA still produces that output, not just that a
recorded number matches.

`source_checksum` and `output_checksum` are equal today because the build is a pure
concatenation with no transform step. ADR-0054 SS2.5 distinguishes them so a future
minification/transform step can diverge from the source checksum without breaking the
schema either output field is read against.

## Consuming this repo

A consumer commits `dist/reelmetrics-design-system.lock` verbatim and copies
`dist/reelmetrics-public.css` (or vendors the `EMBEDDED_CSS` string from
`dist/reelmetrics_design_system.py`) into its own tree. Per ADR-0054 SS2.5, **no**
submodule, subtree, vendored source copy, or pip-style git URL — the lock-plus-rebuild
check above is the entire mechanism.

## Repository role

Registered per ADR-0054 SS2.1 in the workspace's cross-repo sweep scripts
(`scripts/ci_health_check.sh`, `scripts/merge_prs.sh`, `scripts/pull_all.sh`,
`scripts/push_all.sh`) and in `AGENTS.md`, `dev_cycle.md`, and `README.md`.
