import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))

import build as build_mod  # noqa: E402

LANDING_CLASSES = [
    "rm-landing-page",
    "rm-landing-stage",
    "rm-landing-topline",
    "rm-landing-contact",
    "rm-landing-main",
    "rm-landing-wordmark",
    "rm-landing-tagline",
]


def test_landing_hero_classes_present_in_built_css():
    css = build_mod.build()["css"]
    missing = [c for c in LANDING_CLASSES if f".{c}" not in css]
    assert not missing, f"landing hero classes missing from build output: {missing}"


def test_landing_hero_lives_in_components_layer_not_a_new_one():
    css = build_mod.build()["css"]
    components_start = css.index("@layer components {")
    components_end = css.index("\n@layer utilities {")
    components_block = css[components_start:components_end]
    for cls in LANDING_CLASSES:
        assert f".{cls}" in components_block, (
            f".{cls} must live inside @layer components, not a new layer "
            "(ADR-0054 SS2.2 fixes the layer set)"
        )
