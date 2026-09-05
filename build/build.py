#!/usr/bin/env python3
"""Deterministic build: layered CSS source -> dist/ outputs.

Concatenates the CSS layer source files in a fixed read order behind one
`@layer` statement. Cascade precedence comes from that declaration's order
(CSS spec: the first `@layer` statement that names a set of layers fixes
their relative order for the whole stylesheet), not from the order the
per-layer blocks appear in afterward — see ADR-0054 SS2.2.

Three outputs, all consumers can commit verbatim:
  dist/reelmetrics-public.css        the compiled CSS (both consumers link this)
  dist/reelmetrics_design_system.py  same CSS as an embedded Python string
  dist/reelmetrics-design-system.lock  the five fields ADR-0054 SS2.5 names

Running this twice with no source change must produce byte-identical output
in all three files (except a fresh mtime, which no listed field depends on).
That determinism is what backs the consumer-side drift check: refetch this
repo at the lock's committed SHA, rebuild, and compare against the committed
output, rather than trusting a recorded checksum.

T153.02 adds concept themes as a fourth, optional input: any `src/themes/*.css`
file, each expected to open its own `@layer overrides { [data-theme="<name>"] {
...` block (the same self-wrapping convention `tokens.css`/`base.css` already
use for their own layers — see `docs/theme_override_contract.md`). No new
`@layer` name is declared for them; they ride in the existing `overrides`
layer, which is already last in LAYER_DECLARATION and already the named
Bootstrap-override surface, so a concept's tokens always win over both the
base tokens layer and Bootstrap's own overrides regardless of source order.
Discovery is a sorted glob, so read order (and therefore output bytes) is
stable across filesystems; with zero files in `src/themes/`, this appends
nothing and the build is unaffected by the mechanism's presence.

Every discovered theme file is validated against the override contract
before being appended: a `[data-theme="..."]` block may set only a token
already declared in `tokens.css`'s `:root` (a `--rm-*` custom property) or
the one named native-property exception, `color-scheme`. Anything else fails
the build with `ThemeContractViolation` — this is what makes a concept "a
token-override file and nothing else" (ADR-0054 SS3, phase 153 D3) an
enforced contract rather than a convention.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
THEMES_DIR = SRC / "themes"

LAYER_DECLARATION = "@layer reset, tokens, base, components, report, utilities, overrides;\n"

# Read order only needs to be stable for reproducibility — it does not
# control cascade precedence, LAYER_DECLARATION above does that.
SOURCE_FILES = [
    SRC / "tokens.css",
    SRC / "base.css",
    SRC / "components.css",
    SRC / "report.css",
    SRC / "overrides" / "bootstrap.css",
]

# Native CSS properties (not `--rm-*` custom properties) a theme file may
# set directly. `color-scheme` is the one case named by phase 153 D9: a
# concept that flips the page dark needs to be able to say so.
ALLOWED_NATIVE_PROPERTIES = frozenset({"color-scheme"})

_TOKEN_DECL_RE = re.compile(r"(--rm-[a-z0-9-]+)\s*:")
_THEME_RULE_RE = re.compile(r'\[data-theme="[^"]+"\]\s*\{([^}]*)\}', re.DOTALL)
_DECL_RE = re.compile(r"([a-zA-Z0-9-]+)\s*:")


class ThemeContractViolation(Exception):
    """Raised when a src/themes/*.css file sets something other than an
    already-declared --rm-* token or the ALLOWED_NATIVE_PROPERTIES set."""


def allowed_token_names(tokens_css_text: str | None = None) -> set[str]:
    """Every --rm-* custom property declared in tokens.css's :root block —
    the override contract's token allowlist. A theme may only override a
    token that already exists; it may not invent a new one (that is a
    design-system source change, not a concept override, per D3)."""
    if tokens_css_text is None:
        tokens_css_text = (SRC / "tokens.css").read_text()
    return set(_TOKEN_DECL_RE.findall(tokens_css_text))


def discover_theme_files(themes_dir: Path | None = None) -> list[Path]:
    """Sorted glob — deterministic across filesystems. Empty list if the
    directory does not exist yet (true today; T153.04 populates it).
    `themes_dir` defaults to the *current* module-level THEMES_DIR (looked
    up at call time, not bound at def time) so tests can monkeypatch it and
    have read_sources()'s no-arg call pick up the patched value."""
    if themes_dir is None:
        themes_dir = THEMES_DIR
    if not themes_dir.is_dir():
        return []
    return sorted(p for p in themes_dir.glob("*.css") if p.is_file())


def _display_path(path: Path) -> str:
    """path.relative_to(ROOT) for a real repo file; the path itself
    otherwise (test fixtures live under a pytest tmp_path, not ROOT)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate_theme_file(path: Path, text: str, allowed_tokens: set[str]) -> None:
    """Enforce the override contract: every declaration inside a
    `[data-theme="..."]` block must be an already-declared --rm-* token or
    one of ALLOWED_NATIVE_PROPERTIES. Raises ThemeContractViolation naming
    every offending property, not just the first, so a concept author sees
    the whole list in one pass."""
    offenders: list[str] = []
    found_a_rule = False
    for rule_match in _THEME_RULE_RE.finditer(text):
        found_a_rule = True
        body = rule_match.group(1)
        for decl_match in _DECL_RE.finditer(body):
            prop = decl_match.group(1)
            if prop.startswith("--"):
                if prop not in allowed_tokens:
                    offenders.append(prop)
            elif prop not in ALLOWED_NATIVE_PROPERTIES:
                offenders.append(prop)
    if not found_a_rule:
        raise ThemeContractViolation(
            f"{_display_path(path)}: no `[data-theme=\"...\"]` rule found — "
            "a theme file must contain one (see docs/theme_override_contract.md)"
        )
    if offenders:
        raise ThemeContractViolation(
            f"{_display_path(path)} sets propert{'y' if len(offenders) == 1 else 'ies'} "
            f"outside the override contract: {sorted(set(offenders))} — a concept may only "
            "override an existing --rm-* token declared in tokens.css, or color-scheme "
            "(see docs/theme_override_contract.md)"
        )


def read_sources() -> str:
    parts = [LAYER_DECLARATION]
    for f in SOURCE_FILES:
        parts.append(f"\n/* ---- {f.relative_to(ROOT)} ---- */\n")
        parts.append(f.read_text())

    allowed_tokens = allowed_token_names()
    for theme_file in discover_theme_files():
        text = theme_file.read_text()
        validate_theme_file(theme_file, text, allowed_tokens)
        parts.append(f"\n/* ---- {_display_path(theme_file)} ---- */\n")
        parts.append(text)
    return "".join(parts)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def build() -> dict:
    """Pure computation, no filesystem writes — used directly by tests."""
    css = read_sources()
    checksum = sha256(css)
    module = (
        '"""Generated by reelmetric-design-system build/build.py. Do not hand-edit."""\n\n'
        f"SOURCE_CHECKSUM = {checksum!r}\n"
        f"OUTPUT_CHECKSUM = {checksum!r}\n\n"
        f"EMBEDDED_CSS = {css!r}\n"
    )
    sha = git_head_sha()
    lock = (
        "repo: king44444/reelmetric-design-system\n"
        f"commit: {sha}\n"
        f"source_checksum: sha256:{checksum}\n"
        f"output_checksum: sha256:{checksum}\n"
        "build_command: python3 build/build.py\n"
    )
    checksums_txt = f"source  sha256:{checksum}\noutput  sha256:{checksum}\n"
    return {
        "css": css,
        "checksum": checksum,
        "module": module,
        "lock": lock,
        "checksums_txt": checksums_txt,
        "commit": sha,
    }


def main() -> None:
    DIST.mkdir(exist_ok=True)
    try:
        out = build()
    except ThemeContractViolation as exc:
        print(f"BUILD FAILED — theme override contract violation: {exc}", file=sys.stderr)
        sys.exit(1)
    (DIST / "reelmetrics-public.css").write_text(out["css"])
    (DIST / "reelmetrics_design_system.py").write_text(out["module"])
    (DIST / "reelmetrics-design-system.lock").write_text(out["lock"])
    (DIST / "CHECKSUMS.txt").write_text(out["checksums_txt"])

    print(f"Built dist/reelmetrics-public.css ({len(out['css'])} bytes)")
    print(f"checksum sha256:{out['checksum']}")
    print(f"commit   {out['commit']}")


if __name__ == "__main__":
    main()
