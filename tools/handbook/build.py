from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer

from .content_features import part_two
from .content_front import chapter_five, chapter_four, chapter_three, chapter_two, document_map, front_matter, part_one
from .content_ops import part_five_story
from .content_pages import part_three, part_three_workspace
from .content_tech import part_four_story
from .render import gap, rule, table_of_contents
from .theme import (
    BORDER,
    CONTENT_H,
    CONTENT_W,
    DARK_GREY,
    GREY,
    INK,
    LIGHT,
    LIME,
    LOGO,
    MARGIN_BOTTOM,
    MARGIN_TOP,
    MARGIN_X,
    PAGE_H,
    PAGE_W,
    PAPER,
    STYLES,
    TURRET,
)

OUTPUT = Path(__file__).resolve().parents[2] / "AUTHENTIQ-Complete-Guide.pdf"


def flatten(items):
    result = []
    for item in items:
        if isinstance(item, list):
            result.extend(flatten(item))
        elif item is not None:
            result.append(item)
    return result


def draw_cover(canvas, doc) -> None:
    import hashlib

    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(0, 0, 7, PAGE_H, fill=1, stroke=0)

    tile_x, tile_y, tile = 50, PAGE_H - 136, 62
    canvas.setFillColor(PAPER)
    canvas.roundRect(tile_x, tile_y, tile, tile, 12, fill=1, stroke=0)
    canvas.drawImage(LOGO, tile_x + 5, tile_y + 5, tile - 10, tile - 10, mask="auto")

    canvas.setFillColor(PAPER)
    canvas.setFont(TURRET, 17)
    canvas.drawString(tile_x + 78, tile_y + 36, "AUTHENTIQ")
    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 6.8)
    canvas.drawString(tile_x + 79, tile_y + 22, "DIGITAL NOTARY / IP PROTECTION")

    canvas.setFillColor(PAPER)
    canvas.setFont(TURRET, 44)
    canvas.drawString(50, 430, "THE COMPLETE")
    canvas.setFillColor(LIME)
    canvas.drawString(50, 378, "HANDBOOK")

    canvas.setFillColor(LIME)
    canvas.rect(50, 354, 64, 4, fill=1, stroke=0)

    canvas.setFillColor(LIGHT)
    canvas.setFont("Funnel", 11.6)
    canvas.drawString(50, 326, "Every feature, every role, every flow, and the")
    canvas.drawString(50, 308, "entire technology stack behind the product.")

    stats = [("05", "PARTS"), ("41", "CHAPTERS"), ("20", "RANKED FEATURES")]
    x = 50
    for value, label in stats:
        canvas.setFillColor(LIME)
        canvas.setFont(TURRET, 19)
        canvas.drawString(x, 626, value)
        canvas.setFillColor(GREY)
        canvas.setFont("Funnel", 6.2)
        canvas.drawString(x, 614, label)
        x += 118

    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 8)
    canvas.drawString(50, 214, "EDITION 1.0")
    canvas.drawString(50, 200, "NOVEMBER 2026")
    canvas.setFillColor(LIME)
    canvas.setFont("Funnel-Bold", 8.4)
    canvas.drawString(50, 168, "EVIDENCE, NOT ASSUMPTION.")

    digest = hashlib.sha256(b"AUTHENTIQ COMPLETE HANDBOOK 2026").hexdigest()
    bits = bin(int(digest[:36], 16))[2:].zfill(144)
    size, cell_gap = 7.4, 2.1
    start_x = PAGE_W - 50 - (size * 12 + cell_gap * 11)
    start_y = 236
    for index in range(144):
        row, col = divmod(index, 12)
        x = start_x + col * (size + cell_gap)
        y = start_y + (11 - row) * (size + cell_gap)
        canvas.setFillColor(LIME if bits[index] == "1" else colors.HexColor("#454545"))
        canvas.rect(x, y, size, size, fill=1, stroke=0)
    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 6)
    canvas.drawRightString(PAGE_W - 50, 218, "OWNERSHIP DNA / SHA-256 DERIVED")
    canvas.drawRightString(PAGE_W - 50, 208, digest[:32].upper())

    canvas.setFillColor(colors.HexColor("#454545"))
    canvas.setFont("Funnel", 7)
    canvas.drawString(50, 40, "Generated from the running implementation. No invented metrics.")
    canvas.restoreState()


def draw_body(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, PAGE_H - 40, PAGE_W - MARGIN_X, PAGE_H - 40)
    canvas.drawImage(LOGO, MARGIN_X, PAGE_H - 35, 9, 9, mask="auto")
    canvas.setFillColor(INK)
    canvas.setFont(TURRET, 7.2)
    canvas.drawString(MARGIN_X + 14, PAGE_H - 33.5, "AUTHENTIQ")
    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 6.8)
    canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 33.5, "COMPLETE PRODUCT AND TECHNOLOGY HANDBOOK")

    canvas.line(MARGIN_X, 38, PAGE_W - MARGIN_X, 38)
    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 6.8)
    canvas.drawString(MARGIN_X, 27, "AUTHENTIQ  ·  EDITION 1.0  ·  NOVEMBER 2026")
    canvas.setFillColor(INK)
    canvas.setFont("Funnel-Bold", 7.6)
    canvas.drawRightString(PAGE_W - MARGIN_X, 27, f"{doc.page:02d}")
    canvas.setFillColor(LIME)
    canvas.rect(PAGE_W - MARGIN_X - 22, 28.4, 4, 4, fill=1, stroke=0)
    canvas.restoreState()


class HandbookDoc(BaseDocTemplate):
    def afterFlowable(self, flowable) -> None:
        marker = getattr(flowable, "_toc", None)
        if marker is not None:
            level, text = marker
            self.notify("TOCEntry", (level, text, self.page))
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]
            key = f"section-{self.page}-{level}-{slug}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=min(level, 2), closed=False)


def contents_page() -> list:
    return [
        gap(36),
        Paragraph("CONTENTS", ParagraphStyle("toc-title", fontName=TURRET, fontSize=36, leading=40, textColor=INK, spaceAfter=6)),
        Paragraph(
            "Parts, chapters, and the page where each begins.",
            ParagraphStyle("toc-sub", fontName=STYLES["body"].fontName, fontSize=9.2, leading=13, textColor=GREY, spaceAfter=10),
        ),
        rule(CONTENT_W, INK, 0.8),
        gap(10),
        Paragraph(
            "SECTION",
            ParagraphStyle("toc-head", fontName=STYLES["eyebrow"].fontName, fontSize=6.4, leading=8, textColor=GREY),
        ),
        table_of_contents(),
    ]


def build() -> Path:
    doc = HandbookDoc(
        str(OUTPUT),
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="AUTHENTIQ Complete Product and Technology Handbook",
        author="AUTHENTIQ",
        subject="Product, features, roles, flows, and the complete technology stack",
        creator="AUTHENTIQ documentation pipeline",
        keywords="AUTHENTIQ, digital notary, IP protection, zero-knowledge, handbook",
    )
    frame = Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_W, CONTENT_H, id="body")
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[frame], onPage=draw_cover),
            PageTemplate(id="body", frames=[frame], onPage=draw_body),
        ]
    )

    story = [
        NextPageTemplate("body"),
        PageBreak(),
        *front_matter(),
        PageBreak(),
        *document_map(),
        PageBreak(),
        *contents_page(),
        PageBreak(),
        *part_one(),
        PageBreak(),
        *part_two(),
        PageBreak(),
        *part_three(),
        *part_three_workspace(),
        PageBreak(),
        *part_four_story(),
        PageBreak(),
        *part_five_story(),
    ]

    doc.multiBuild(flatten(story))
    print(f"Wrote {OUTPUT}")
    print(f"Pages: {doc.page}")
    return OUTPUT


if __name__ == "__main__":
    build()
