import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))

import build as build_mod  # noqa: E402


def test_build_is_reproducible():
    """Running the build twice with no source change must be byte-identical
    (mtime-independent fields only) -- this is what the consumer-side drift
    check (ADR-0054 SS2.5) relies on: rebuild at a pinned commit and compare."""
    first = build_mod.build()
    second = build_mod.build()
    assert first["css"] == second["css"]
    assert first["checksum"] == second["checksum"]
    assert first["module"] == second["module"]
    assert first["lock"] == second["lock"]


def test_layer_declaration_matches_adr_0054():
    out = build_mod.build()
    assert out["css"].startswith(build_mod.LAYER_DECLARATION)
    assert build_mod.LAYER_DECLARATION.strip() == (
        "@layer reset, tokens, base, components, report, utilities, overrides;"
    )


def test_every_declared_layer_is_actually_filled():
    out = build_mod.build()
    for layer in ["reset", "tokens", "base", "components", "report", "utilities", "overrides"]:
        assert f"@layer {layer} {{" in out["css"], f"layer '{layer}' never opened in the built CSS"


def test_embedded_python_module_carries_the_same_css():
    out = build_mod.build()
    ns: dict = {}
    exec(out["module"], ns)
    assert ns["EMBEDDED_CSS"] == out["css"]
    assert ns["SOURCE_CHECKSUM"] == out["checksum"]
    assert ns["OUTPUT_CHECKSUM"] == out["checksum"]


def test_lock_file_carries_all_five_adr_0054_fields():
    out = build_mod.build()
    lock = out["lock"]
    for field in ["repo:", "commit:", "source_checksum:", "output_checksum:", "build_command:"]:
        assert field in lock, f"lock file missing required field {field!r}"
    assert "king44444/reelmetric-design-system" in lock
    assert "sha256:" in lock


def test_source_files_read_in_a_stable_fixed_order():
    names = [f.name for f in build_mod.SOURCE_FILES]
    assert names == [
        "tokens.css",
        "base.css",
        "components.css",
        "report.css",
        "bootstrap.css",
    ]


def test_no_javascript_toolchain_anywhere_in_the_repo():
    """ADR-0054 SS2.3: Python only, no package.json/node_modules/npm, anywhere
    in the repo or its CI."""
    hits = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.name == "package.json" or path.name == "node_modules":
            hits.append(str(path))
    assert hits == [], f"JS toolchain artifact(s) found: {hits}"

    workflows_dir = ROOT / ".github" / "workflows"
    for wf in workflows_dir.glob("*.yml"):
        text = wf.read_text()
        assert "npm" not in text and "npx" not in text, f"{wf} references npm/npx"
