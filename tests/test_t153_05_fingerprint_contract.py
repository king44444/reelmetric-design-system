"""T153.05 / ADR-0055 SS2.2 -- the fixed fingerprint color contract.

Two things must hold, proven live rather than asserted from source (T152.06's
precedent for these guards, per docs/theme_override_contract.md):

1. A theme file may not set any `--rm-fingerprint-*` token, even though it is
   a declared `--rm-*` custom property the normal allowlist would otherwise
   admit (build/build.py's FORBIDDEN_TOKEN_PREFIX).
2. The eight fixed hex values never render outside a `.rm-fingerprint`-scoped
   rule in the compiled CSS -- reused for document chrome, headings,
   buttons, badges, status states, tables, or an unrelated chart would be a
   release-blocking visual-contract failure per the ADR-0055 briefing.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import build as build_mod  # noqa: E402

FINGERPRINT_HEXES = {
    "--rm-fingerprint-drama": "#355070",
    "--rm-fingerprint-comedy": "#e9c46a",
    "--rm-fingerprint-action": "#e76f51",
    "--rm-fingerprint-thriller-suspense": "#6d597a",
    "--rm-fingerprint-horror": "#5a2333",
    "--rm-fingerprint-romance": "#b56576",
    "--rm-fingerprint-sci-fi-fantasy": "#2d8c8c",
    "--rm-fingerprint-family-inspirational": "#f4a261",
}


def test_all_eight_fingerprint_tokens_are_declared_in_tokens_css():
    tokens_css = (ROOT / "src" / "tokens.css").read_text()
    for token, hexval in FINGERPRINT_HEXES.items():
        assert f"{token}: {hexval}" in tokens_css, f"{token} missing or wrong value in tokens.css"


def test_theme_file_setting_a_fingerprint_token_is_rejected(tmp_path):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    (themes_dir / "_probe.css").write_text(
        '@layer overrides {\n[data-theme="_probe"] {\n'
        "--rm-fingerprint-drama: #ff00aa;\n"
        "}\n}\n"
    )
    allowed = build_mod.allowed_token_names()
    # --rm-fingerprint-drama IS in the normal allowlist (it's a declared
    # --rm-* token) -- the rejection must come from FORBIDDEN_TOKEN_PREFIX,
    # not from the token being undeclared.
    assert "--rm-fingerprint-drama" in allowed
    theme_file = themes_dir / "_probe.css"
    with pytest.raises(build_mod.ThemeContractViolation, match="fingerprint"):
        build_mod.validate_theme_file(theme_file, theme_file.read_text(), allowed)


def test_no_committed_theme_file_sets_a_fingerprint_token():
    """Belt-and-suspenders: even if a future theme file slipped past review,
    the build must still reject it -- but no committed file should rely on
    that catch. Runs the real validator against every real file on disk."""
    allowed = build_mod.allowed_token_names()
    for theme_file in build_mod.discover_theme_files():
        text = theme_file.read_text()
        try:
            build_mod.validate_theme_file(theme_file, text, allowed)
        except build_mod.ThemeContractViolation as exc:
            pytest.fail(f"{theme_file.name} fails the override contract: {exc}")


_FINGERPRINT_TOKEN_REF_RE = re.compile(r"--rm-fingerprint-[a-z-]+")
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def test_fingerprint_tokens_and_hexes_render_only_inside_rm_fingerprint_scope():
    """Parse the compiled CSS's rules and assert every one that references a
    --rm-fingerprint-* token, or hardcodes one of the eight reserved hex
    values, is scoped under `.rm-fingerprint` -- except tokens.css's own
    :root declaration block, which *defines* the tokens rather than *using*
    them and is exempted by name."""
    out = build_mod.build()
    css = out["css"]
    offenders = []
    for selector, body in _RULE_RE.findall(css):
        selector = selector.strip()
        if selector == ":root":
            continue  # the declaration, not a use
        uses_token = bool(_FINGERPRINT_TOKEN_REF_RE.search(body))
        uses_hex = any(hexval in body for hexval in FINGERPRINT_HEXES.values())
        if (uses_token or uses_hex) and ".rm-fingerprint" not in selector:
            offenders.append(selector)
    assert not offenders, (
        "fingerprint token/hex referenced outside .rm-fingerprint scope: "
        f"{offenders}"
    )
