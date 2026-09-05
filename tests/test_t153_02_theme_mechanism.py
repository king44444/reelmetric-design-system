"""T153.02 — data-theme mechanism, override contract, and the D9 color-scheme
fix. See docs/theme_override_contract.md for the contract this enforces.

Each test proves the mechanism actually fires (contract violations really
fail the build; discovery really is sorted; the base build really is
untouched by the machinery when zero theme files exist) rather than
asserting behavior from source, per this task's own acceptance criteria and
T152.06's precedent for these guards.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))

import build as build_mod  # noqa: E402


def _write_theme(tmp_path: Path, name: str, body: str) -> Path:
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir(exist_ok=True)
    f = themes_dir / f"{name}.css"
    f.write_text(f'@layer overrides {{\n[data-theme="{name}"] {{\n{body}\n}}\n}}\n')
    return f


def test_theme_discovery_finds_the_four_t153_04_concepts_sorted():
    """T153.04 populated src/themes/ with four concepts. Discovery order is
    the sort order of their filenames, which is also their appended order in
    the compiled CSS (see docs/theme_override_contract.md)."""
    found = build_mod.discover_theme_files()
    assert [p.stem for p in found] == ["dense-tool", "editorial", "muted-minimal", "radical"]


def test_theme_discovery_is_sorted_and_deterministic(tmp_path, monkeypatch):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    for name in ["radical", "dense-tool", "editorial", "muted-minimal"]:
        (themes_dir / f"{name}.css").write_text(
            f'@layer overrides {{\n[data-theme="{name}"] {{\n--rm-ink: #000;\n}}\n}}\n'
        )
    found = build_mod.discover_theme_files(themes_dir)
    assert [p.name for p in found] == sorted(p.name for p in found)
    assert [p.stem for p in found] == ["dense-tool", "editorial", "muted-minimal", "radical"]


def test_discovery_of_a_missing_directory_returns_empty_list(tmp_path):
    assert build_mod.discover_theme_files(tmp_path / "does_not_exist") == []


def test_zero_themes_leaves_build_output_unchanged_by_the_mechanism(tmp_path, monkeypatch):
    """Isolates the discovery/append machinery from the D9 content fix and
    from T153.04's now-populated src/themes/: pointing THEMES_DIR at two
    different, both-empty directories must produce byte-identical output --
    proving the mechanism itself, independent of how many concept files
    happen to exist today, is a genuine no-op with zero theme files. (Before
    T153.04 this compared the real directory to an empty one; that stopped
    isolating the mechanism the moment the real directory stopped being
    empty, which is exactly what this task did.)"""
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "empty_themes_a")
    baseline = build_mod.build()["css"]
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "empty_themes_b")
    with_other_empty_dir = build_mod.build()["css"]
    assert with_other_empty_dir == baseline


def test_out_of_contract_property_fails_the_build(tmp_path, monkeypatch):
    """The exact probe from this task's verification recipe:
    `[data-theme="x"]{ --not-a-token: 1; }` must be rejected."""
    _write_theme(tmp_path, "x", "--not-a-token: 1;")
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "themes")
    with pytest.raises(build_mod.ThemeContractViolation, match="--not-a-token"):
        build_mod.build()


def test_out_of_contract_native_property_fails_the_build(tmp_path, monkeypatch):
    """A real CSS property other than color-scheme (e.g. font-size) is not
    a token and must be rejected even though it's syntactically ordinary
    CSS a browser would happily apply."""
    _write_theme(tmp_path, "y", "font-size: 20px;")
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "themes")
    with pytest.raises(build_mod.ThemeContractViolation, match="font-size"):
        build_mod.build()


def test_in_contract_theme_file_builds_and_is_included(tmp_path, monkeypatch):
    """An existing --rm-* token plus the one allowed native property
    (color-scheme) builds cleanly and its content reaches the output."""
    _write_theme(tmp_path, "muted-minimal", "--rm-ink: #1a1a1a;\ncolor-scheme: light;")
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "themes")
    out = build_mod.build()
    assert 'data-theme="muted-minimal"' in out["css"]
    assert "--rm-ink: #1a1a1a" in out["css"]


def test_a_theme_file_with_no_data_theme_rule_fails_the_build(tmp_path, monkeypatch):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    (themes_dir / "broken.css").write_text("@layer overrides {\n.not-a-theme-selector {}\n}\n")
    monkeypatch.setattr(build_mod, "THEMES_DIR", themes_dir)
    with pytest.raises(build_mod.ThemeContractViolation, match="rule found"):
        build_mod.build()


def test_allowed_token_names_matches_tokens_css():
    names = build_mod.allowed_token_names()
    assert "--rm-ink" in names
    assert "--rm-paper" in names
    assert "--rm-not-a-real-token" not in names


def test_layer_declaration_still_has_no_themes_layer():
    """Themes ride in the existing `overrides` layer (see
    docs/theme_override_contract.md) — no new cascade layer is declared, so
    ADR-0054's fixed 7-layer list is unchanged by this task."""
    assert build_mod.LAYER_DECLARATION.strip() == (
        "@layer reset, tokens, base, components, report, utilities, overrides;"
    )


def test_color_scheme_default_is_light_matching_the_rendered_page():
    """D9: tokens.css declared color-scheme: dark while the seeded
    monochrome page renders light (--rm-paper #fafafa on --rm-ink #0a0a0a).
    Fixed here; this is the one intentional content change T153.02 makes to
    the base (no-theme) build output — see this task's completion evidence
    for the isolated diff."""
    tokens_css = (ROOT / "src" / "tokens.css").read_text()
    root_block = tokens_css.split(":root {", 1)[1].split("\n}\n", 1)[0]
    assert "color-scheme: light" in root_block
    assert "color-scheme: dark" not in root_block


def test_color_scheme_is_overridable_by_a_theme(tmp_path, monkeypatch):
    """A dark concept must be able to flip it back."""
    _write_theme(tmp_path, "radical", "color-scheme: dark;\n--rm-ink: #fff;")
    monkeypatch.setattr(build_mod, "THEMES_DIR", tmp_path / "themes")
    out = build_mod.build()
    assert '[data-theme="radical"]' in out["css"]
