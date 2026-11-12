export interface DuplicateMatch {
  registration_id: string;
  id: string;
  title: string;
  file_name: string;
  asset_type: string;
  registered_at: string | null;
  similarity: number;
  method: string;
  owned_by_you: boolean;
  same_organization: boolean;
}

export interface DuplicateReport {
  exact_matches: DuplicateMatch[];
  similar_matches: DuplicateMatch[];
  checked: boolean;
  explanation: string;
}

export function hasDuplicates(report: DuplicateReport | null) {
  if (!report) return false;
  return report.exact_matches.length > 0 || report.similar_matches.length > 0;
}

export async function perceptualHash(file: File): Promise<string | null> {
  if (!file.type.startsWith("image/")) return null;
  try {
    const bitmap = await createImageBitmap(file);
    const canvas = document.createElement("canvas");
    canvas.width = 9;
    canvas.height = 8;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return null;
    context.drawImage(bitmap, 0, 0, 9, 8);
    bitmap.close();
    const { data } = context.getImageData(0, 0, 9, 8);
    const luma = new Array<number>(72);
    for (let index = 0; index < 72; index += 1) {
      const offset = index * 4;
      luma[index] = 0.299 * data[offset] + 0.587 * data[offset + 1] + 0.114 * data[offset + 2];
    }
    let bits = "";
    for (let row = 0; row < 8; row += 1) {
      for (let column = 0; column < 8; column += 1) {
        bits += luma[row * 9 + column] > luma[row * 9 + column + 1] ? "1" : "0";
      }
    }
    return BigInt(`0b${bits}`).toString(16).padStart(16, "0");
  } catch {
    return null;
  }
}
