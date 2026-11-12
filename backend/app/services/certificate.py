from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.config import settings

NAVY = HexColor("#FFFFFF")
SIDEBAR = HexColor("#EAEAEA")
CARD = HexColor("#FFFFFF")
BLUE = HexColor("#171717")
VIOLET = HexColor("#454545")
GREEN = HexColor("#5B7D00")
AMBER = HexColor("#454545")
WHITE = HexColor("#171717")
MUTED = HexColor("#888888")
LINE = HexColor("#D0D0D0")
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "authentiq-logo.png"


def _logo(pdf: canvas.Canvas, x: float, y: float, size: float):
    if LOGO_PATH.exists():
        pdf.drawImage(ImageReader(str(LOGO_PATH)), x, y, width=size, height=size, mask="auto")


def _field(pdf: canvas.Canvas, label: str, value: str, x: float, y: float, width: float = 480):
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(x, y, label.upper())
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 10.5)
    text = str(value)
    while pdf.stringWidth(text, "Helvetica-Bold", 10.5) > width and len(text) > 12:
        text = text[:-4] + "..."
    pdf.drawString(x, y - 14, text)


def _build_qr(url: str) -> ImageReader:
    image = qrcode.make(url)
    buffer = __import__("io").BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def build_registration_certificate(registration, creator_name: str, verification_url: str) -> bytes:
    buffer = __import__("io").BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFillColor(NAVY)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(SIDEBAR)
    pdf.roundRect(32, 32, width - 64, height - 64, 18, fill=1, stroke=0)
    pdf.setStrokeColor(LINE)
    pdf.roundRect(32, 32, width - 64, height - 64, 18, fill=0, stroke=1)

    _logo(pdf, 58, height - 117, 46)
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(114, height - 86, "AUTHENTIQ")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(114, height - 101, "DECENTRALIZED DIGITAL NOTARY")

    pdf.setFillColor(BLUE)
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(60, height - 175, "Digital Ownership")
    pdf.drawString(60, height - 210, "Certificate")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(60, height - 232, "Tamper-evident registration of a digital creation")
    pdf.setStrokeColor(LINE)
    pdf.line(60, height - 250, width - 60, height - 250)

    rows = [
        ("Registration ID", registration.registration_id),
        ("File name", registration.file_name),
        ("SHA-256 fingerprint", registration.sha256),
        ("Ownership commitment", registration.commitment),
        ("Poseidon commitment", registration.poseidon_commitment),
        ("Creator", creator_name),
        ("Registration timestamp", registration.registered_at.strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Ledger transaction ID", registration.ledger_tx_id or "Pending"),
        ("Ledger mode", registration.ledger_mode),
        ("Network", "AUTHENTIQ Local Ledger" if registration.ledger_mode == "simulation" else "Polygon Amoy"),
    ]
    y = height - 280
    for label, value in rows:
        _field(pdf, label, value, 60, y)
        y -= 36

    qr = _build_qr(verification_url)
    pdf.drawImage(qr, width - 175, 120, 105, 105, mask="auto")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(width - 176, 106, "Scan to verify")

    pdf.setFillColor(CARD)
    pdf.roundRect(60, 90, width - 300, 44, 8, fill=1, stroke=0)
    pdf.setFillColor(AMBER if registration.ledger_mode == "simulation" else GREEN)
    pdf.setFont("Helvetica-Bold", 8)
    label = "SIMULATED LEDGER RECORD" if registration.ledger_mode == "simulation" else "POLYGON AMOY TESTNET RECORD"
    pdf.drawString(74, 112, label)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    detail = (
        "This record was written to the AUTHENTIQ append-only local ledger simulation. "
        "It is not a public blockchain transaction."
        if registration.ledger_mode == "simulation"
        else "This record references a Polygon Amoy testnet transaction. Testnet records have no monetary value."
    )
    pdf.drawString(74, 100, detail[:120])

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(60, 60, "This certificate evidences a cryptographic registration record. It is not a legal determination of authorship.")
    pdf.drawString(60, 50, f"Verification URL: {verification_url}")
    pdf.setFillColor(VIOLET)
    pdf.drawString(width - 155, 60, "authentiq.protocol")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_idea_certificate(idea, creator_name: str, verification_url: str) -> bytes:
    buffer = __import__("io").BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFillColor(NAVY)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(SIDEBAR)
    pdf.roundRect(32, 32, width - 64, height - 64, 18, fill=1, stroke=0)
    pdf.setStrokeColor(LINE)
    pdf.roundRect(32, 32, width - 64, height - 64, 18, fill=0, stroke=1)
    _logo(pdf, 58, height - 117, 46)
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(114, height - 86, "AUTHENTIQ")
    pdf.setFillColor(VIOLET)
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(60, height - 175, "Idea Protection")
    pdf.drawString(60, height - 210, "Certificate")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(60, height - 232, "Private commitment timestamp for an unpublished idea")
    pdf.setStrokeColor(LINE)
    pdf.line(60, height - 250, width - 60, height - 250)

    rows = [
        ("Idea reference", idea.idea_ref),
        ("Idea title", idea.title),
        ("Commitment", idea.commitment),
        ("Creator", creator_name),
        ("Protected at", idea.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Ledger transaction ID", idea.ledger_tx_id or "Pending"),
        ("Ledger mode", idea.ledger_mode),
        ("Privacy setting", idea.privacy),
    ]
    y = height - 280
    for label, value in rows:
        _field(pdf, label, value, 60, y)
        y -= 36

    pdf.setFillColor(CARD)
    pdf.roundRect(60, 105, width - 120, 52, 8, fill=1, stroke=0)
    pdf.setFillColor(AMBER)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(74, 138, "PRIVATE IDEA CONTENT IS NOT ON THE LEDGER")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(74, 124, "The ledger stores only this commitment and timestamp. The idea description remains encrypted at rest.")
    pdf.drawString(74, 113, "A commitment demonstrates prior possession of the described content; it is not a legal determination of ownership.")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(60, 80, f"Verification URL: {verification_url}")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def verification_url_for(identifier: str) -> str:
    return f"{settings.public_app_url}/verify/{identifier}"
