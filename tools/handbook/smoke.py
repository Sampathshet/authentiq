from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph

from .render import callout, chapter, feature_card, gap, kv, lead, numbers, p, part_opener, stat_row, table, bullets, h2, table_of_contents
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


def draw_cover(canvas, doc) -> None:
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

    canvas.setFillColor(GREY)
    canvas.setFont("Funnel", 8)
    canvas.drawString(50, 214, "EDITION 1.0")
    canvas.drawString(50, 200, "NOVEMBER 2026")
    canvas.setFillColor(LIME)
    canvas.setFont("Funnel-Bold", 8.4)
    canvas.drawString(50, 168, "EVIDENCE, NOT ASSUMPTION.")

    import hashlib

    digest = hashlib.sha256(b"AUTHENTIQ COMPLETE HANDBOOK 2026").hexdigest()
    bits = bin(int(digest[:36], 16))[2:].zfill(144)
    size, cell_gap = 7.4, 2.1
    start_x, start_y = PAGE_W - 50 - (size * 12 + cell_gap * 11), 236
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
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)

    def afterFlowable(self, flowable) -> None:
        marker = getattr(flowable, "_toc", None)
        if marker is not None:
            level, text = marker
            self.notify("TOCEntry", (level, text, self.page))


def build_smoke(output: Path) -> None:
    doc = HandbookDoc(
        str(output),
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="AUTHENTIQ Handbook Smoke",
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
        Paragraph("CONTENTS", ParagraphStyle("toc-title", fontName=TURRET, fontSize=36, leading=40, textColor=INK, spaceAfter=16)),
        gap(4),
        table_of_contents(),
        PageBreak(),
        *part_opener("I", "ORIENTATION", "What the product is, who it serves, and how a session unfolds from first visit to signed-in work.", [(1, "What AUTHENTIQ is"), (2, "What the website does")], note="This part is the map. Read it first if you are new to the product; the rest of the handbook assumes you know these five chapters."),
        *chapter(1, "What AUTHENTIQ is", "Orientation", "AUTHENTIQ is a digital notary and intellectual-property protection workspace. It records cryptographic fingerprints of creative work, proves ownership without revealing secrets, and preserves an append-only history of every important action."),
        stat_row([("41", "backend tests"), ("29", "database tables"), ("20", "ranked features")]),
        gap(12),
        h2("The honest one-paragraph answer"),
        p("AUTHENTIQ answers four questions about a creative artifact: what exact bytes existed, who registered them, when the record was written, and how ownership changed. It answers them with SHA-256 hashes, Poseidon commitments, zero-knowledge proofs, certificates, and a hash-chained history. It does not call itself a law firm, and it does not pretend a local ledger is a public blockchain."),
        lead("Registration is evidence of priority. It is not an automatic legal determination of authorship."),
        callout("Why the wording matters", "Every claim in this handbook is tied to code that exists. Where the system cannot do something, it says so instead of filling the gap with a fabricated result."),
        *bullets(["Real SHA-256 over exact file bytes.", "Real Poseidon commitments on BN254.", "Real Schnorr proofs, generated and verified at runtime."]),
        *table(["Layer", "Question", "Mechanism"], [["Content", "What bytes?", "SHA-256 fingerprint"], ["Ownership", "Who knows the secret?", "Poseidon commitment and Schnorr proof"], ["History", "When and in what order?", "Append-only ledger and audit chain"]], widths=[80, 190, 225], bold_first=True),
        feature_card(1, "Zero-knowledge ownership proofs", "Prove you know the opening of a commitment without publishing the file or the secret.", [("What it is", "A non-interactive Schnorr proof over BN254 G1 that demonstrates knowledge of the commitment opening."), ("How it works", bullets(["The owner requests a one-time challenge nonce.", "The server compares the local file hash with the registered fingerprint.", "The proof is bound to the registration, commitment, and nonce.", "A verifier checks the equation without learning the secret."]))]),
        *chapter(2, "What the website does", "Orientation", "The site has a public marketing surface, a signed-in workspace, and a disclosure-limited verification surface. Each has a different audience and a different security posture."),
        h2("Three surfaces, one product"),
        kv([("Public", "Landing page, sign-up, sign-in, password reset, and public verification links."), ("Workspace", "Twenty protected pages for registration, proof, collaboration, and review."), ("Verification", "A no-login page that reveals only fields the owner approved.")]),
        *numbers(["A visitor reads the landing page and creates an account.", "A creator uploads a file and registers its fingerprint.", "The server writes a ledger event and issues a certificate.", "The owner generates a proof or a silent-sharing link.", "A verifier checks the proof without seeing the file.", "Teams, transfers, alerts, and disputes preserve the rest of the history."]),
    ]
    for index, thing in enumerate(story):
        if isinstance(thing, list):
            print("LIST AT", index, thing)
    doc.multiBuild(story)


if __name__ == "__main__":
    build_smoke(Path(__file__).resolve().parents[2] / "_smoke.pdf")
