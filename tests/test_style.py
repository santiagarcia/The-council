"""Generated presentation fixtures test observation fidelity and privacy."""

import hashlib
import json
from io import BytesIO

import pytest
import yaml
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from council.store import CouncilError
from council.style import ingest


def fixture_deck(repo):
    """Make a small deterministic-content deck with formatting and structural cues."""
    path = repo / "style_sources/presentations/private/CONFIDENTIAL-FILENAME.pptx"
    deck = Presentation()
    deck.slide_width = Inches(12)
    deck.slide_height = Inches(6.75)
    for title in ("Introduction", "Preliminary results", "Next steps", "Thank you"):
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = title
        run = slide.shapes.title.text_frame.paragraphs[0].runs[0]
        run.font.name = "Arial"
        run.font.size = Pt(32)
        slide.placeholders[1].text = "SECRET-SCIENTIFIC-RESULT is not exported"
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(255, 255, 255)
    deck.save(path)
    return path


def test_ingest_observations_source_preservation_and_no_content_export(repo):
    source = fixture_deck(repo)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    guide = repo / "style/presentation-style-guide.md"
    guide.write_text(
        guide.read_text(encoding="utf-8") + "\nManual decision: retain this sentence.\n",
        encoding="utf-8",
    )
    result = ingest(repo, "style_sources/presentations/private")
    assert "1 decks / 4 slides" in result
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    profile_path = repo / "style/derived/presentation-style-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text())
    deck = profile["observations"][0]
    assert deck["dimensions_inches"] == {"width": 12, "height": 6.75}
    assert deck["direct_fonts_by_run"]["Arial"] == 4
    assert deck["font_hierarchy_pt"]["title"]["median"] == 32
    assert deck["backgrounds"]["rgb:FFFFFF"] == 4
    assert deck["opening_category"] == "opening"
    assert deck["closing_category"] == "closing"
    assert deck["plot_labeling"] == "manual review required"
    assert len(deck["title_positions_normalized"]) == 4
    for path in (repo / "style").rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "SECRET-SCIENTIFIC-RESULT" not in text
            assert "CONFIDENTIAL-FILENAME" not in text
    before_reports = {p: p.read_bytes() for p in (repo / "style").rglob("*") if p.is_file()}
    ingest(repo, "style_sources/presentations/private")
    assert all(p.read_bytes() == content for p, content in before_reports.items())
    assert "Manual decision: retain this sentence." in guide.read_text(encoding="utf-8")


def test_empty_ingestion_and_dry_run(repo):
    before = {p: p.read_bytes() for p in (repo / "style").rglob("*") if p.is_file()}
    preview = json.loads(ingest(repo, "style_sources/presentations/private", dry_run=True))
    assert preview["deck_count"] == 0
    assert all(p.read_bytes() == content for p, content in before.items())
    assert not (repo / "style/derived/deck-inventory.json").exists()
    ingest(repo, "style_sources/presentations/private")
    assert json.loads((repo / "style/derived/deck-inventory.json").read_text())["decks"] == []
    assert "No decks available" in (repo / "style/derived/style-observations.md").read_text()


def test_corrupt_deck_and_broken_markers_do_not_write(repo):
    source = repo / "style_sources/presentations/private/broken.pptx"
    source.write_bytes(b"not a zip")
    with pytest.raises(CouncilError, match="no reports were written"):
        ingest(repo, "style_sources/presentations/private")
    assert not (repo / "style/derived/deck-inventory.json").exists()


def test_broken_guide_markers_preserve_manual_work(repo):
    guide = repo / "style/presentation-style-guide.md"
    guide.write_text("Manual prose\n<!-- council:observations:start -->\n", encoding="utf-8")
    with pytest.raises(CouncilError, match="markers"):
        ingest(repo, "style_sources/presentations/private")
    assert guide.read_text() == "Manual prose\n<!-- council:observations:start -->\n"
    assert not (repo / "style/derived/deck-inventory.json").exists()


def test_linked_pictures_do_not_crash_or_fetch_resources(repo):
    path = fixture_deck(repo)
    deck = Presentation(path)
    image = BytesIO()
    Image.new("RGB", (2, 2), "white").save(image, format="PNG")
    image.seek(0)
    picture = deck.slides[0].shapes.add_picture(image, Inches(1), Inches(1))
    blip = picture._element.xpath(".//a:blip")[0]
    del blip.attrib[qn("r:embed")]
    blip.set(qn("r:link"), "rIdExternalFixture")
    deck.save(path)
    ingest(repo, "style_sources/presentations/private")
    profile = yaml.safe_load((repo / "style/derived/presentation-style-profile.yaml").read_text())
    assert profile["observations"][0]["features"]["pictures_without_embedded_data"] == 1
