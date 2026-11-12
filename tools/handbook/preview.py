import sys
from pathlib import Path

import pymupdf

pdf = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
pages = [int(value) for value in sys.argv[3:]] if len(sys.argv) > 3 else None
out_dir.mkdir(parents=True, exist_ok=True)
doc = pymupdf.open(pdf)
targets = pages or range(1, doc.page_count + 1)
for number in targets:
    page = doc[number - 1]
    pixmap = page.get_pixmap(dpi=130)
    path = out_dir / f"page-{number:02d}.png"
    pixmap.save(path)
    print(path.name)
print("pages", doc.page_count)
