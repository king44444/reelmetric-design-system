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


def test_shared_hero_does_not_force_a_tall_blank_lead_in():
    css = build_mod.build()["css"]
    root_block = css.split(":root {", 1)[1].split("\n}", 1)[0]
    hero_block = css.split(".rm-hero {", 1)[1].split("\n}", 1)[0]
    assert "--rm-hero-min-height: clamp(360px, 46vh, 500px);" in root_block
    assert "min-height: var(--rm-hero-min-height);" in hero_block
    assert "min-height: 780px;" not in hero_block


def test_shared_hero_content_is_not_centered_into_a_blank_band():
    css = build_mod.build()["css"]
    hero_content_block = css.split(".rm-hero-content {", 1)[1].split("\n}", 1)[0]
    assert "align-self: start;" in hero_content_block
    assert "align-self: center;" not in hero_content_block


def test_shared_hero_protects_dark_page_readability():
    css = build_mod.build()["css"]
    root_block = css.split(":root {", 1)[1].split("\n}", 1)[0]
    hero_kicker_block = css.split(".rm-hero .rm-kicker {", 1)[1].split("\n}", 1)[0]
    hero_title_block = css.split(".rm-hero h1 {", 1)[1].split("\n}", 1)[0]
    assert "--rm-hero-kicker: rgba(247, 239, 225, 0.76);" in root_block
    assert "--rm-hero-h1-max-width: 15ch;" in root_block
    assert "--rm-hero-h1-size: min(var(--rm-text-4xl), 4.25rem);" in root_block
    assert "color: var(--rm-hero-kicker);" in hero_kicker_block
    assert "max-width: var(--rm-hero-h1-max-width);" in hero_title_block
    assert "font-size: var(--rm-hero-h1-size);" in hero_title_block


def test_shared_cta_protects_dark_panel_readability():
    css = build_mod.build()["css"]
    root_block = css.split(":root {", 1)[1].split("\n}", 1)[0]
    cta_block = css.split(".rm-cta {", 1)[1].split("\n}", 1)[0]
    cta_kicker_block = css.split(".rm-cta .rm-kicker {", 1)[1].split("\n}", 1)[0]
    cta_lead_block = css.split(".rm-cta .rm-lead {", 1)[1].split("\n}", 1)[0]
    assert "--rm-cta-fg: var(--rm-cream);" in root_block
    assert "--rm-cta-kicker: rgba(247, 239, 225, 0.78);" in root_block
    assert "--rm-cta-lead: rgba(247, 239, 225, 0.76);" in root_block
    assert "color: var(--rm-cta-fg);" in cta_block
    assert "color: var(--rm-cta-kicker);" in cta_kicker_block
    assert "color: var(--rm-cta-lead);" in cta_lead_block


def test_landing_contact_link_keeps_wordmark_styling():
    css = build_mod.build()["css"]
    landing_contact_block = css.split(".rm-landing-contact {", 1)[1].split("\n}", 1)[0]
    assert "color: inherit;" in landing_contact_block
    assert "text-decoration: none;" in landing_contact_block


BRAND_LANDING_CLASSES = [
    "rm-brand-landing",
    "rm-brand-stage",
    "rm-brand-topline",
    "rm-brand-footline",
    "rm-brand-main",
    "rm-brand-logo",
    "rm-brand-rule",
    "rm-brand-tagline",
]


def test_brand_landing_classes_live_in_components_layer():
    css = build_mod.build()["css"]
    components_start = css.index("@layer components {")
    components_end = css.index("\n@layer utilities {")
    components_block = css[components_start:components_end]
    missing = [c for c in BRAND_LANDING_CLASSES if f".{c}" not in components_block]
    assert not missing, f"brand landing classes missing from @layer components: {missing}"


def test_brand_landing_uses_the_style_guide_primary_palette():
    css = build_mod.build()["css"]
    root_block = css.split(":root {", 1)[1].split("\n}", 1)[0]
    assert "--rm-brand-black: #000000;" in root_block
    assert "--rm-brand-white: #ffffff;" in root_block
    assert "--rm-brand-gold: #d09705;" in root_block
    assert "Futura" in root_block.split("--rm-brand-font-display:", 1)[1].split(";", 1)[0]


def test_brand_landing_motion_respects_reduced_motion():
    css = build_mod.build()["css"]
    reduced = css.split(".rm-brand-tagline {", 1)[1]
    assert "@media (prefers-reduced-motion: reduce)" in reduced
    assert "animation: none;" in reduced.split("@media (prefers-reduced-motion: reduce)", 1)[1]
