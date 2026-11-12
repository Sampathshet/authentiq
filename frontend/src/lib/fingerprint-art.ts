export interface DnaCell {
  x: number;
  y: number;
  filled: boolean;
  weight: number;
}

export function fingerprintCells(seed: string, columns = 9, rows = 9): DnaCell[] {
  const hex = (seed || "").toLowerCase().replace(/[^0-9a-f]/g, "") || "0";
  const cells: DnaCell[] = [];
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const index = (row * columns + column) * 3;
      const a = parseInt(hex[index % hex.length] ?? "0", 16);
      const b = parseInt(hex[(index + 1) % hex.length] ?? "0", 16);
      const c = parseInt(hex[(index + 2) % hex.length] ?? "0", 16);
      cells.push({
        x: column,
        y: row,
        filled: a + b > 12,
        weight: (a * 16 + b + c) % 256,
      });
    }
  }
  return cells;
}

export function ownershipDnaSvg(seed: string, label = "AUTHENTIQ ownership fingerprint"): string {
  const cells = fingerprintCells(seed);
  const cellSize = 12;
  const size = 9 * cellSize + 16;
  const rects = cells
    .map((cell) => {
      if (!cell.filled) return "";
      const shade = cell.weight > 190 ? "#171717" : cell.weight > 110 ? "#454545" : "#B7FF00";
      return `<rect x="${8 + cell.x * cellSize}" y="${8 + cell.y * cellSize}" width="${cellSize - 2}" height="${cellSize - 2}" rx="1.5" fill="${shade}"/>`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="${label}"><rect width="${size}" height="${size}" fill="#EAEAEA"/><rect x="1" y="1" width="${size - 2}" height="${size - 2}" fill="none" stroke="#D0D0D0" rx="6"/>${rects}</svg>`;
}

export function downloadSvg(seed: string, filename: string) {
  const svg = ownershipDnaSvg(seed);
  const blob = new Blob([svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
