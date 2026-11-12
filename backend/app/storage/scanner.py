import re
from pathlib import PurePosixPath

BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".vbs",
    ".jar", ".sh", ".php", ".asp", ".aspx", ".jsp", ".cgi", ".hta", ".lnk",
}
DOUBLE_EXTENSION_PATTERN = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|png|jpe?g|txt)\.(exe|bat|cmd|ps1|js|vbs|scr|msi)$", re.I)
EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


def scan_bytes(filename: str, data: bytes, allowed_extensions: list[str]) -> dict:
    threats = []
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix in BLOCKED_EXTENSIONS:
        threats.append(f"Blocked executable extension: {suffix}")
    if suffix and allowed_extensions and suffix not in allowed_extensions:
        threats.append(f"File extension is not in the allowed list: {suffix}")
    if DOUBLE_EXTENSION_PATTERN.search(filename):
        threats.append("Suspicious double extension detected")
    if EICAR_MARKER in data:
        threats.append("Malware test signature detected")
    return {
        "clean": len(threats) == 0,
        "threats": threats,
        "engine": "AUTHENTIQ built-in signature scanner",
        "note": "This is a development scanner integration point. Replace with ClamAV or a production scanning service.",
    }


def scan_path(filename: str, path, allowed_extensions: list[str]) -> dict:
    sample = b""
    with path.open("rb") as handle:
        sample = handle.read(1024 * 1024)
    return scan_bytes(filename, sample, allowed_extensions)
