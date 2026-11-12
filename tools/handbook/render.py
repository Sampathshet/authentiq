from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from .theme import (
    BORDER,
    CONTENT_W,
    DARK_GREY,
    GREY,
    INK,
    LIGHT,
    LIME,
    PAPER,
    STYLES,
    TURRET,
)


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def h2(text: str) -> Paragraph:
    return Paragraph(text, STYLES["h2"])


def h3(text: str) -> Paragraph:
    return Paragraph(text, STYLES["h3"])


def lead(text: str) -> Paragraph:
    return Paragraph(text, STYLES["lead"])


def gap(height: float = 8) -> Spacer:
    return Spacer(1, height)


def rule(width: float = CONTENT_W, color=BORDER, thickness: float = 0.6) -> Table:
    bar = Table([[""]], colWidths=[width], rowHeights=[thickness])
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return bar


def bullets(items: list[str], style: str = "bullet") -> list[Paragraph]:
    return [
        Paragraph(f'<font color="#B7FF00">•</font>&nbsp;&nbsp;{item}', STYLES[style])
        for item in items
    ]


def compact_bullets(items: list[str]) -> list[Paragraph]:
    style = ParagraphStyle(
        "card-bullet",
        fontName=STYLES["feature_body"].fontName,
        fontSize=8.4,
        leading=11.8,
        textColor=INK,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=1.4,
    )
    return [
        Paragraph(f'<font color="#B7FF00">•</font>&nbsp;&nbsp;{item}', style)
        for item in items
    ]


def numbers(items: list[str], style: str = "number") -> list[Paragraph]:
    result = []
    for index, item in enumerate(items, start=1):
        result.append(
            Paragraph(
                f'<font color="#888888">{index:02d}</font>&nbsp;&nbsp;&nbsp;{item}',
                STYLES[style],
            )
        )
    return result


def checklist(items: list[str]) -> list[Paragraph]:
    return [
        Paragraph(
            f'<font color="#B7FF00">•</font>&nbsp;&nbsp;{item}',
            STYLES["bullet"],
        )
        for item in items
    ]


def callout(label: str, body: str, tone: str = "light") -> Table:
    if tone == "lime":
        background = LIME
        bar = LIME
        label_style = ParagraphStyle("cl-label-lime", parent=STYLES["eyebrow"], textColor=INK)
        body_style = ParagraphStyle("cl-body-lime", parent=STYLES["body"], textColor=INK, spaceAfter=0)
    elif tone == "ink":
        background = INK
        bar = LIME
        label_style = ParagraphStyle("cl-label-ink", parent=STYLES["eyebrow"], textColor=GREY)
        body_style = ParagraphStyle("cl-body-ink", parent=STYLES["body"], textColor=PAPER, spaceAfter=0)
    else:
        background = LIGHT
        bar = LIME
        label_style = ParagraphStyle("cl-label-light", parent=STYLES["eyebrow"], textColor=GREY)
        body_style = ParagraphStyle("cl-body-light", parent=STYLES["body"], textColor=INK, spaceAfter=0)

    content = [Paragraph(label.upper(), label_style), Paragraph(body, body_style)]
    box = Table([[content]], colWidths=[CONTENT_W])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return box


def table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[float] | None = None,
    bold_first: bool = False,
    caption: str | None = None,
    mono_last: bool = False,
    font_size: float | None = None,
) -> list:
    count = len(headers)
    if widths is None:
        widths = [CONTENT_W / count] * count
    data = [[Paragraph(header.upper(), STYLES["th"]) for header in headers]]
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            if index == 0 and bold_first:
                style = STYLES["td_bold"]
            elif mono_last and index == len(row) - 1:
                style = STYLES["td_mono"]
            else:
                style = STYLES["td"]
            cells.append(Paragraph(value, style))
        data.append(cells)
    grid = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, LIGHT]),
    ]
    grid.setStyle(TableStyle(commands))
    result: list = [grid]
    if caption:
        result.append(Paragraph(caption, STYLES["caption"]))
    else:
        result.append(Spacer(1, 9))
    return result


def kv(rows: list[tuple[str, str]], label_width: float = 128) -> Table:
    data = []
    for label, value in rows:
        data.append([Paragraph(label.upper(), STYLES["kv_label"]), Paragraph(value, STYLES["kv_value"])])
    grid = Table(data, colWidths=[label_width, CONTENT_W - label_width], hAlign="LEFT")
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
            ]
        )
    )
    return [grid, Spacer(1, 9)]


def stat_row(items: list[tuple[str, str]]) -> Table:
    cells = []
    labels = []
    for value, label in items:
        cells.append(Paragraph(value, ParagraphStyle("stat", fontName=TURRET, fontSize=25, leading=28, textColor=LIME)))
        cells.append(Paragraph(label.upper(), ParagraphStyle("stat-label", fontName=STYLES["eyebrow"].fontName, fontSize=6.6, leading=9, textColor=LIGHT)))
        labels.append(label)
    grid = Table([cells], colWidths=[CONTENT_W / (len(items) * 2)] * (len(items) * 2), hAlign="LEFT")
    grid.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), INK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
            ]
        )
    )
    return grid


def feature_card(
    rank: int,
    title: str,
    tagline: str,
    sections: list[tuple[str, object]],
) -> KeepTogether:
    rank_cell = [
        Paragraph(f"{rank:02d}", STYLES["rank"]),
    ]
    footer = "OF 20"
    rank_cell.append(Paragraph(footer, ParagraphStyle("rank-foot", fontName=STYLES["eyebrow"].fontName, fontSize=5.4, leading=7, textColor=LIGHT, alignment=1)))

    inner_rows = []
    for label, value in sections:
        if isinstance(value, str):
            cell = [Paragraph(value, STYLES["feature_body"])]
        else:
            cell = value
        inner_rows.append([Paragraph(label.upper(), STYLES["feature_label"]), cell])

    inner = Table(inner_rows, colWidths=[58, CONTENT_W - 46 - 24 - 58], hAlign="LEFT")
    inner.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    content = [
        Paragraph("FEATURE", ParagraphStyle("f-eyebrow", fontName=STYLES["eyebrow"].fontName, fontSize=6.4, leading=8, textColor=GREY)),
        Paragraph(title, STYLES["feature_title"]),
        Paragraph(tagline, STYLES["feature_tag"]),
        inner,
    ]

    outer = Table([[rank_cell, content]], colWidths=[46, CONTENT_W - 46], hAlign="LEFT")
    outer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), INK),
                ("BACKGROUND", (1, 0), (1, 0), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEABOVE", (0, 0), (-1, 0), 2, LIME),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 4),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 0), (0, 0), 11),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
                ("RIGHTPADDING", (1, 0), (1, 0), 12),
                ("TOPPADDING", (1, 0), (1, 0), 10),
                ("BOTTOMPADDING", (1, 0), (1, 0), 11),
            ]
        )
    )
    return KeepTogether([outer, Spacer(1, 12)])


def chapter(number: int, title: str, kicker: str, intro: str) -> list:
    marker = rule(CONTENT_W, BORDER, 0.8)
    marker._toc = (1, f"{number:02d}   {title}")
    header = KeepTogether(
        [
            Paragraph(f"CHAPTER {number:02d}  ·  {kicker.upper()}", STYLES["eyebrow"]),
            Paragraph(title, ParagraphStyle("chapter-title", fontName=TURRET, fontSize=25, leading=28, textColor=INK, spaceAfter=7)),
            Paragraph(intro, ParagraphStyle("chapter-intro", parent=STYLES["intro"], spaceAfter=11)),
        ]
    )
    return [Spacer(1, 30), header, marker, Spacer(1, 12)]


def part_opener(number: str, title: str, intro: str, chapters: list[tuple[int, str]], note: str | None = None) -> list:
    marker = Table([[""]], colWidths=[CONTENT_W], rowHeights=[1])
    marker._toc = (0, f"PART {number}   {title}")
    compact = len(chapters) > 10
    rows = []
    for chapter_number, chapter_title in chapters:
        rows.append(
            [
                Paragraph(
                    f"{chapter_number:02d}",
                    ParagraphStyle(
                        "pt-num",
                        fontName=TURRET,
                        fontSize=11.2 if compact else 13,
                        leading=14 if compact else 16,
                        textColor=LIME,
                    ),
                ),
                Paragraph(
                    chapter_title,
                    ParagraphStyle(
                        "pt-title",
                        fontName=STYLES["body"].fontName,
                        fontSize=8.7 if compact else 9.6,
                        leading=11.4 if compact else 13,
                        textColor=INK,
                    ),
                ),
            ]
        )
    listing = Table(rows, colWidths=[42, CONTENT_W - 42], hAlign="LEFT")
    listing.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2 if compact else 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2 if compact else 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
            ]
        )
    )
    story = [
        gap(46),
        Paragraph(f"PART {number}", STYLES["eyebrow"]),
        Paragraph(title, ParagraphStyle("part-title", fontName=TURRET, fontSize=38, leading=42, textColor=INK, spaceAfter=10)),
        rule(72, LIME, 5),
        gap(14),
        Paragraph(intro, ParagraphStyle("part-intro", parent=STYLES["lead"], fontSize=11.2, leading=16.8)),
    ]
    if note:
        story.append(
            Paragraph(
                note,
                ParagraphStyle("part-note", fontName=STYLES["body"].fontName, fontSize=8.6, leading=12.6, textColor=GREY, spaceBefore=4),
            )
        )
    story.extend(
        [
            gap(22 if compact else 30),
            Paragraph("IN THIS PART", STYLES["eyebrow"]),
            listing,
            gap(18),
            Paragraph(
                f"PART {number} OF V",
                ParagraphStyle("part-tail", fontName=STYLES["eyebrow"].fontName, fontSize=6.4, leading=8, textColor=GREY),
            ),
            marker,
        ]
    )
    return story


def table_of_contents() -> TableOfContents:
    toc = TableOfContents()
    toc.levelStyles = [STYLES["toc0"], STYLES["toc1"]]
    toc.dotsMinLevel = -1
    return toc


def code_block(lines: list[str]) -> Table:
    body = "<br/>".join(escape(line).replace(" ", "&nbsp;") for line in lines)
    cell = Paragraph(body, STYLES["code"])
    box = Table([[cell]], colWidths=[CONTENT_W])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return box
