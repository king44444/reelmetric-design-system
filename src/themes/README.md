# `src/themes/`

Each file here is one visual concept, discovered by `build/build.py` in sorted
filename order and enforced against the override contract at build time. See
[`docs/theme_override_contract.md`](../../docs/theme_override_contract.md) for
the full rule; the short version:

```css
/* src/themes/<name>.css */
@layer overrides {
[data-theme="<name>"] {
  --rm-ink: #111111;
  /* ...only already-declared --rm-* tokens from tokens.css, plus the one
     native-property exception, color-scheme... */
  color-scheme: dark;
}
}
```

- **Filename == theme name.** `src/themes/radical.css` backs `data-theme="radical"`.
- **Self-wrap in `@layer overrides`.** The same convention `tokens.css`
  (`@layer tokens`) and `base.css` (`@layer reset`/`@layer base`) already use.
  No new `@layer` name is declared for themes — they ride in the existing,
  already-last `overrides` layer, so a concept's tokens always win over the
  base tokens layer and over Bootstrap's own overrides, regardless of source
  order.
- **Tokens only.** A theme may set a `--rm-*` custom property that already
  exists in `tokens.css`'s `:root`, or the native `color-scheme` property.
  Anything else — a new custom property name, a literal color on a real
  selector, a font-size, a layout change — fails the build with
  `ThemeContractViolation`. A concept that needs more than that is out of
  contract (phase 153 D3) and gets reported, not quietly accommodated.
- **This directory is empty as of T153.02.** The mechanism is built here;
  authoring the four concepts is T153.04's job.
