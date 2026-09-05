# Theme override contract

T153.02, per phase 153 D3: *"A concept is a token-override file and nothing
else."* This document is the contract's authoritative statement; it is
enforced by `build/build.py::validate_theme_file` (a build failure, not a
lint warning) and exercised by `tests/test_t153_02_theme_mechanism.py`.

## What a theme file is

One file per concept at `src/themes/<name>.css`, discovered by `build.py` in
sorted order and appended to the compiled output inside the existing
`overrides` cascade layer (no new layer name is declared — see the module
docstring in `build/build.py` and ADR-0054 §2.2's fixed
`@layer reset, tokens, base, components, report, utilities, overrides;`
declaration, which this task leaves unchanged).

```css
@layer overrides {
[data-theme="muted-minimal"] {
  --rm-ink: #1a1a1a;
  --rm-muted: #6b6b6b;
  color-scheme: light;
}
}
```

## What a theme file may set

1. **Any `--rm-*` custom property already declared in `src/tokens.css`'s
   `:root` block.** The theme *overrides* an existing token's value for
   elements under `[data-theme="<name>"]` (custom properties inherit, so
   setting `data-theme` on one ancestor — per T153.06, `<body>` — covers the
   whole page). It may **not** invent a new token name: a name that doesn't
   already exist in `tokens.css` is a design-system source change, not a
   concept override, and belongs in a follow-up to this task, not in a theme
   file.
2. **`color-scheme`, and nothing else, as a native (non-custom-property)
   CSS property.** This is the one named exception (phase 153 D9): a concept
   whose page renders dark needs to be able to say so. No other native
   property — no `font-size`, `background`, `padding`, `border`, selector
   restructuring, or anything else — may appear in a theme file. A concept
   that needs one is out of contract (D3) and must be reported as a finding
   naming the missing token, not resolved by widening this list or by
   editing a consuming template.

## Enforcement

`build/build.py`'s `validate_theme_file` parses every declaration inside each
discovered file's `[data-theme="..."]` block and raises
`ThemeContractViolation` — which `main()` turns into a nonzero exit and a
named list of every offending property — for anything outside the two rules
above. `make build` therefore fails on an out-of-contract theme file; it does
not silently accept or truncate it.

## Why an allowlist, not a denylist

The token allowlist is *derived* from `tokens.css` at build time
(`allowed_token_names()`), not hand-maintained as a second list that can go
stale. This mirrors phase 153 D5's fix to the color-hue guards in both
consumers' contract tests: a fixed denylist only ever catches what someone
already thought to forbid, and a concept introducing something genuinely new
passes it by accident. An allowlist derived from the thing it's checking
against stays correct as that thing changes.

## What this does not cover yet

`color-scheme`'s *default* value (`src/tokens.css`'s `:root` block) was
itself wrong before this task — declared `dark` while the seeded monochrome
page renders light (T151.10: `--rm-paper #fafafa` / `--rm-ink #0a0a0a`) — and
is corrected to `light` as part of landing this contract (D9). That one-line
content fix is intentional and is called out separately in T153.02's
completion evidence; it is not part of the *mechanism* this document
describes, which is provably inert with zero theme files present (see
`test_zero_themes_leaves_build_output_unchanged_by_the_mechanism`).
