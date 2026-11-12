import { api, sha256Hex } from "@/lib/api";

export interface UploadState {
  upload_id: string;
  filename: string;
  size_bytes: number;
  total_chunks: number;
  chunk_size: number;
  uploaded_chunks: number;
  status: string;
  final_sha256?: string | null;
}

export interface UploadProgress {
  phase: "fingerprinting" | "uploading" | "finalizing" | "complete";
  currentChunk: number;
  totalChunks: number;
  percent: number;
  chunkSha256?: string;
  message: string;
}

export async function uploadFileChunked(
  file: File,
  onProgress: (progress: UploadProgress) => void,
): Promise<{ upload: UploadState; sha256: string }> {
  const chunkSize = 4 * 1024 * 1024;
  const totalChunks = Math.max(1, Math.ceil(file.size / chunkSize));
  onProgress({
    phase: "fingerprinting",
    currentChunk: 0,
    totalChunks,
    percent: 1,
    message: "Computing the canonical SHA-256 fingerprint in your browser",
  });
  const buffer = await file.arrayBuffer();
  const sha256 = await sha256Hex(buffer);

  const upload = await api.post<UploadState>("/uploads/initiate", {
    filename: file.name,
    size_bytes: file.size,
    mime_type: file.type || "application/octet-stream",
    total_chunks: totalChunks,
    chunk_size: chunkSize,
    client_sha256: sha256,
  });

  for (let index = 0; index < totalChunks; index += 1) {
    const start = index * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunk = buffer.slice(start, end);
    const chunkHash = await sha256Hex(chunk);
    const form = new FormData();
    form.append("chunk_index", String(index));
    form.append("sha256", chunkHash);
    form.append("file", new Blob([chunk], { type: file.type || "application/octet-stream" }), `${file.name}.part${index}`);
    await api.postForm<UploadState>(`/uploads/${upload.upload_id}/chunk`, form);
    onProgress({
      phase: "uploading",
      currentChunk: index + 1,
      totalChunks,
      percent: Math.round(((index + 1) / totalChunks) * 90),
      chunkSha256: chunkHash,
      message: `Chunk ${index + 1} of ${totalChunks} verified`,
    });
  }

  onProgress({
    phase: "finalizing",
    currentChunk: totalChunks,
    totalChunks,
    percent: 94,
    message: "Reassembling, scanning, encrypting, and verifying the overall fingerprint",
  });
  const completeForm = new FormData();
  completeForm.append("client_sha256", sha256);
  const completed = await api.postForm<UploadState>(`/uploads/${upload.upload_id}/complete`, completeForm);
  if (completed.final_sha256 && completed.final_sha256 !== sha256) {
    throw new Error("The server fingerprint does not match the browser fingerprint");
  }
  onProgress({
    phase: "complete",
    currentChunk: totalChunks,
    totalChunks,
    percent: 100,
    message: "Encrypted at rest and fingerprinted",
  });
  return { upload: completed, sha256 };
}
