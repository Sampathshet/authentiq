from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = Path(__file__).resolve().parent / "fonts"
LOGO = ROOT / "backend" / "app" / "assets" / "authentiq-logo.png"

INK = colors.HexColor("#171717")
LIME = colors.HexColor("#B7FF00")
LIGHT = colors.HexColor("#EAEAEA")
PAPER = colors.HexColor("#FFFFFF")
DARK_GREY = colors.HexColor("#454545")
GREY = colors.HexColor("#888888")
BORDER = colors.HexColor("#D0D0D0")

PAGE_W, PAGE_H = A4
MARGIN_X = 50
MARGIN_TOP = 58
MARGIN_BOTTOM = 52
CONTENT_W = PAGE_W - MARGIN_X * 2
CONTENT_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM

FUNNEL = "Funnel"
FUNNEL_BOLD = "Funnel-Bold"
TURRET = "Turret"


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont(FUNNEL, str(FONT_DIR / "FunnelDisplay-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FUNNEL_BOLD, str(FONT_DIR / "FunnelDisplay-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(TURRET, str(FONT_DIR / "Turret_Road-Regular.ttf")))
    pdfmetrics.registerFontFamily(
        FUNNEL,
        normal=FUNNEL,
        bold=FUNNEL_BOLD,
        italic=FUNNEL,
        boldItalic=FUNNEL_BOLD,
    )


register_fonts()


def build_styles() -> dict[str, ParagraphStyle]:
    styles: dict[str, ParagraphStyle] = {}

    styles["body"] = ParagraphStyle(
        "body",
        fontName=FUNNEL,
        fontSize=9.2,
        leading=13.8,
        textColor=INK,
        spaceAfter=6.5,
        alignment=TA_LEFT,
        splitLongWords=True,
    )
    styles["body_tight"] = ParagraphStyle(
        "body_tight",
        parent=styles["body"],
        spaceAfter=3,
    )
    styles["lead"] = ParagraphStyle(
        "lead",
        fontName=FUNNEL,
        fontSize=11.2,
        leading=17,
        textColor=DARK_GREY,
        spaceAfter=9,
    )
    styles["intro"] = ParagraphStyle(
        "intro",
        fontName=FUNNEL,
        fontSize=9.6,
        leading=14.6,
        textColor=DARK_GREY,
        spaceAfter=7,
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        fontName=TURRET,
        fontSize=16,
        leading=19,
        textColor=INK,
        spaceBefore=15,
        spaceAfter=5,
        keepWithNext=True,
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        fontName=FUNNEL_BOLD,
        fontSize=10.2,
        leading=13.4,
        textColor=INK,
        spaceBefore=11,
        spaceAfter=2.5,
        keepWithNext=True,
    )
    styles["eyebrow"] = ParagraphStyle(
        "eyebrow",
        fontName=FUNNEL_BOLD,
        fontSize=7,
        leading=9,
        textColor=GREY,
        spaceAfter=5,
    )
    styles["small"] = ParagraphStyle(
        "small",
        fontName=FUNNEL,
        fontSize=8,
        leading=11.6,
        textColor=DARK_GREY,
    )
    styles["caption"] = ParagraphStyle(
        "caption",
        fontName=FUNNEL,
        fontSize=7.2,
        leading=10,
        textColor=GREY,
        spaceBefore=4,
        spaceAfter=8,
    )
    styles["th"] = ParagraphStyle(
        "th",
        fontName=FUNNEL_BOLD,
        fontSize=7,
        leading=9,
        textColor=PAPER,
    )
    styles["td"] = ParagraphStyle(
        "td",
        fontName=FUNNEL,
        fontSize=7.9,
        leading=11,
        textColor=INK,
    )
    styles["td_bold"] = ParagraphStyle(
        "td_bold",
        parent=styles["td"],
        fontName=FUNNEL_BOLD,
    )
    styles["td_mono"] = ParagraphStyle(
        "td_mono",
        fontName=FUNNEL,
        fontSize=7.4,
        leading=10,
        textColor=INK,
        splitLongWords=True,
    )
    styles["kv_label"] = ParagraphStyle(
        "kv_label",
        fontName=FUNNEL_BOLD,
        fontSize=7,
        leading=10.5,
        textColor=GREY,
    )
    styles["kv_value"] = ParagraphStyle(
        "kv_value",
        fontName=FUNNEL,
        fontSize=8.3,
        leading=11.6,
        textColor=INK,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        parent=styles["body"],
        leftIndent=14,
        firstLineIndent=-14,
        spaceAfter=3.4,
    )
    styles["number"] = ParagraphStyle(
        "number",
        parent=styles["body"],
        leftIndent=22,
        firstLineIndent=-22,
        spaceAfter=4.2,
    )
    styles["quote"] = ParagraphStyle(
        "quote",
        fontName=FUNNEL,
        fontSize=12,
        leading=18,
        textColor=INK,
        spaceBefore=2,
        spaceAfter=2,
    )
    styles["code"] = ParagraphStyle(
        "code",
        fontName=FUNNEL,
        fontSize=7.6,
        leading=11,
        textColor=INK,
    )
    styles["feature_title"] = ParagraphStyle(
        "feature_title",
        fontName=FUNNEL_BOLD,
        fontSize=12.6,
        leading=15.5,
        textColor=INK,
        spaceAfter=2,
    )
    styles["feature_tag"] = ParagraphStyle(
        "feature_tag",
        fontName=FUNNEL,
        fontSize=8.4,
        leading=11.6,
        textColor=DARK_GREY,
        spaceAfter=7,
    )
    styles["feature_label"] = ParagraphStyle(
        "feature_label",
        fontName=FUNNEL_BOLD,
        fontSize=6.8,
        leading=9.6,
        textColor=GREY,
        spaceBefore=5,
    )
    styles["feature_body"] = ParagraphStyle(
        "feature_body",
        fontName=FUNNEL,
        fontSize=8.5,
        leading=12,
        textColor=INK,
        spaceAfter=1,
    )
    styles["rank"] = ParagraphStyle(
        "rank",
        fontName=TURRET,
        fontSize=21,
        leading=23,
        textColor=LIME,
        alignment=1,
    )
    styles["toc0"] = ParagraphStyle(
        "toc0",
        fontName=FUNNEL_BOLD,
        fontSize=9.4,
        leading=14,
        textColor=INK,
        spaceBefore=11,
        spaceAfter=2,
        keepWithNext=True,
    )
    styles["toc1"] = ParagraphStyle(
        "toc1",
        fontName=FUNNEL,
        fontSize=8.7,
        leading=13.4,
        textColor=DARK_GREY,
        leftIndent=14,
    )
    return styles


STYLES = build_styles()
