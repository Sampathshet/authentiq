import { format, formatDistanceToNow, parseISO } from "date-fns";

export function formatDate(value?: string | null, pattern = "MMM d, yyyy HH:mm") {
  if (!value) return "Not available";
  try {
    return format(parseISO(value), pattern);
  } catch {
    return value;
  }
}

export function formatShortDate(value?: string | null) {
  return formatDate(value, "MMM d, yyyy");
}

export function relativeTime(value?: string | null) {
  if (!value) return "unknown";
  try {
    return formatDistanceToNow(parseISO(value), { addSuffix: true });
  } catch {
    return value;
  }
}

export function truncateMiddle(value?: string | null, head = 10, tail = 8) {
  if (!value) return "Unavailable";
  if (value.length <= head + tail + 3) return value;
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

export function formatBytes(bytes?: number | null) {
  if (bytes === undefined || bytes === null) return "Unavailable";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function titleCase(value?: string | null) {
  if (!value) return "Unavailable";
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function percent(value?: number | null) {
  if (value === undefined || value === null) return "Unavailable";
  return `${Math.round(value * 100)}%`;
}

export function initials(name?: string | null) {
  if (!name) return "AQ";
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function pluralize(count: number, singular: string, plural?: string) {
  return `${count} ${count === 1 ? singular : plural || `${singular}s`}`;
}

export const assetTypeOptions = [
  { value: "image", label: "Image" },
  { value: "document", label: "Document" },
  { value: "pdf", label: "PDF" },
  { value: "source_code", label: "Source code" },
  { value: "design", label: "Design" },
  { value: "research", label: "Research paper" },
  { value: "audio", label: "Audio" },
  { value: "video", label: "Video" },
  { value: "ai_generated", label: "AI-generated creation" },
  { value: "other", label: "Other" },
];

export const privacyOptions = [
  { value: "private", label: "Private", hint: "Only you and your organization can view the record." },
  { value: "public_fingerprint", label: "Public fingerprint", hint: "Anyone with the reference can confirm the fingerprint exists. Never listed publicly." },
  { value: "public", label: "Public record", hint: "Listed in the public records registry with your display name, title, fingerprint, and timestamp." },
];

export const statusTone: Record<string, string> = {
  registered: "blue",
  verified: "green",
  disputed: "amber",
  pending: "slate",
  pending_recipient: "amber",
  recipient_accepted: "blue",
  completed: "green",
  rejected: "red",
  cancelled: "slate",
  open: "amber",
  under_review: "blue",
  evidence_requested: "violet",
  resolved: "green",
  new: "amber",
  dismissed: "slate",
  active: "green",
  invited: "amber",
  declined: "red",
  proposed: "amber",
  approved: "green",
  superseded: "slate",
  failed: "red",
  expired: "slate",
  revoked: "red",
  private: "slate",
  public: "green",
  public_fingerprint: "blue",
  submitted: "blue",
  protected: "violet",
  revealed: "green",
  ownership_approved: "green",
};

export const alertTypeLabels: Record<string, string> = {
  exact_match: "Exact fingerprint match",
  perceptual_similarity: "Perceptual similarity",
  near_duplicate: "Near duplicate",
};

export function humanizeAction(action: string) {
  return action
    .replace(/[_.]/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function proofStatement() {
  return "The default proof demonstrates knowledge of the Pedersen commitment opening without revealing the private secret. The file SHA-256 is compared locally and on the server, but hash equality is not enforced inside the default sigma proof.";
}
