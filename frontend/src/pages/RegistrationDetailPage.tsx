import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  Archive,
  Award,
  CheckCircle2,
  CopyCheck,
  Download,
  Eye,
  FileClock,
  Fingerprint,
  Gavel,
  GitCompareArrows,
  KeyRound,
  Layers,
  Link2,
  Lock,
  PlusCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { OwnershipDna } from "@/components/common/ownership-dna";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { Field, InfoRow } from "@/components/common/field";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { FileDropzone } from "@/components/common/file-dropzone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { api, downloadResponse, extractErrorMessage, fetchObjectUrl, sha256Hex } from "@/lib/api";
import { uploadFileChunked, type UploadProgress } from "@/lib/upload";
import { formatBytes, formatDate, percent, relativeTime, titleCase } from "@/lib/format";
import type { AlertItem, OwnershipChain, ProofResult, Registration, ShareItem, TrustReport, VersionItem } from "@/lib/types";

type RegistrationDetail = Registration & { has_private_access?: boolean };

interface ProofItem {
  id: string;
  scheme: string;
  status: string;
  public_signals: Record<string, unknown>;
  created_at: string;
  verified_at: string | null;
}

interface VerificationState {
  registration_id: string;
  fingerprint: string;
  commitment: string;
  ledger_tx_id: string | null;
  ledger_mode: string;
  ledger_record: Record<string, unknown> | null;
  proofs: ProofItem[];
}

interface ProvenanceItem {
  id: string;
  declared_ai: boolean;
  model_name?: string | null;
  tool_name?: string | null;
  human_contribution?: string | null;
  editing_details?: string | null;
  prompt_commitment?: string | null;
  analysis_available: boolean;
  created_at: string;
  ledger_tx_id?: string | null;
}

interface ProvenanceResponse {
  items: ProvenanceItem[];
  analysis_available: boolean;
  disclaimer: string;
}

interface TransferItem {
  id: string;
  status: string;
  from_name?: string | null;
  to_name?: string | null;
  to_email: string;
  created_at: string;
  completed_at?: string | null;
  ledger_tx_id?: string | null;
}

interface CompareResponse {
  same_fingerprint: boolean;
  left: VersionItem;
  right: VersionItem;
  differences: Record<string, boolean>;
}

interface ShareCreateResponse {
  verification_id: string;
  verification_url: string;
  expires_at: string;
  max_uses: number;
  disclosure: Record<string, boolean>;
  proof_system: string;
  proof_package: Record<string, unknown>;
}

const disclosureLabels: Record<string, string> = {
  show_reference: "Show the registration reference",
  show_registration_date: "Show the registration timestamp",
  show_fingerprint: "Show the SHA-256 fingerprint",
  show_organization: "Show organization membership",
  anonymous: "Hide the creator identity",
};

export default function RegistrationDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [versionOpen, setVersionOpen] = useState(false);
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [versionNote, setVersionNote] = useState("");
  const [versionBusy, setVersionBusy] = useState(false);
  const [versionProgress, setVersionProgress] = useState<UploadProgress | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareHours, setShareHours] = useState("72");
  const [shareUses, setShareUses] = useState("3");
  const [shareMessage, setShareMessage] = useState("");
  const [disclosure, setDisclosure] = useState<Record<string, boolean>>({
    show_reference: true,
    show_registration_date: true,
    show_fingerprint: false,
    show_organization: false,
    anonymous: true,
  });
  const [shareBusy, setShareBusy] = useState(false);
  const [createdShare, setCreatedShare] = useState<ShareCreateResponse | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferEmail, setTransferEmail] = useState("");
  const [transferReason, setTransferReason] = useState("");
  const [transferBusy, setTransferBusy] = useState(false);
  const [disputeOpen, setDisputeOpen] = useState(false);
  const [disputeReason, setDisputeReason] = useState("");
  const [disputeDescription, setDisputeDescription] = useState("");
  const [disputeBusy, setDisputeBusy] = useState(false);
  const [leftVersion, setLeftVersion] = useState("");
  const [rightVersion, setRightVersion] = useState("");
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [packetBusy, setPacketBusy] = useState(false);
  const [verificationKey, setVerificationKey] = useState<string | null>(null);
  const [verificationKeyBusy, setVerificationKeyBusy] = useState(false);

  const registrationQuery = useQuery({
    queryKey: ["registration", id],
    queryFn: () => api.get<RegistrationDetail>(`/registrations/${encodeURIComponent(id)}`),
  });
  const registration = registrationQuery.data;
  const ownership = registration?.ownership;
  const isOwner = ownership ? ownership.is_owner : true;
  const pendingTransfer = ownership?.pending_transfer ?? null;

  const verificationQuery = useQuery({
    queryKey: ["verification-state", id],
    queryFn: () => api.get<VerificationState>(`/registrations/${encodeURIComponent(id)}/verification-state`),
    enabled: !!registration,
  });
  const trustQuery = useQuery({
    queryKey: ["trust-score", id],
    queryFn: () => api.get<TrustReport>(`/registrations/${encodeURIComponent(id)}/trust-score`),
    enabled: !!registration,
  });
  const versionsQuery = useQuery({
    queryKey: ["versions", id],
    queryFn: () => api.get<{ items: VersionItem[] }>(`/versions/registration/${encodeURIComponent(id)}`),
    enabled: !!registration,
  });
  const proofsQuery = useQuery({
    queryKey: ["proofs", id],
    queryFn: () => api.get<{ items: ProofItem[] }>(`/zkp/proofs/${encodeURIComponent(id)}`),
    enabled: !!registration,
  });
  const sharesQuery = useQuery({
    queryKey: ["shares"],
    queryFn: () => api.get<{ items: ShareItem[] }>("/sharing"),
    enabled: !!registration,
  });
  const provenanceQuery = useQuery({
    queryKey: ["provenance-registration", id],
    queryFn: () => api.get<ProvenanceResponse>(`/provenance/${encodeURIComponent(id)}`),
    enabled: !!registration,
  });
  const transfersQuery = useQuery({
    queryKey: ["transfer-history", id],
    queryFn: () => api.get<{ items: TransferItem[] }>(`/transfers/history/${encodeURIComponent(id)}`),
    enabled: !!registration,
  });
  const ownershipChainQuery = useQuery({
    queryKey: ["ownership-chain", id],
    queryFn: () => api.get<OwnershipChain>(`/registrations/${encodeURIComponent(id)}/ownership-chain`),
    enabled: !!registration,
  });
  const compareQuery = useQuery({
    queryKey: ["compare", leftVersion, rightVersion],
    queryFn: () => api.get<CompareResponse>(`/versions/compare?left=${leftVersion}&right=${rightVersion}`),
    enabled: !!leftVersion && !!rightVersion && leftVersion !== rightVersion,
  });

  const alertsQuery = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get<{ items: AlertItem[] }>("/alerts?page_size=50"),
    enabled: !!registration,
  });

  const duplicateAlerts = useMemo(
    () =>
      (alertsQuery.data?.items || []).filter(
        (alert) =>
          alert.registration_id === registration?.id || alert.matched_registration_id === registration?.id,
      ),
    [alertsQuery.data, registration?.id],
  );

  const relevantShares = useMemo(
    () => (sharesQuery.data?.items || []).filter((share) => share.registration_label === registration?.registration_id),
    [sharesQuery.data, registration?.registration_id],
  );

  const refresh = () => {
    registrationQuery.refetch();
    verificationQuery.refetch();
    versionsQuery.refetch();
    proofsQuery.refetch();
    sharesQuery.refetch();
    provenanceQuery.refetch();
    transfersQuery.refetch();
    ownershipChainQuery.refetch();
  };

  if (registrationQuery.isLoading) return <LoadingBlock rows={8} />;
  if (registrationQuery.isError || !registration) return <ErrorState error={registrationQuery.error} onRetry={() => registrationQuery.refetch()} />;

  const preview = async () => {
    if (registration.mime_type.startsWith("image/") || registration.mime_type === "application/pdf" || registration.mime_type.startsWith("text/")) {
      setPreviewLoading(true);
      setPreviewOpen(true);
      try {
        const url = await fetchObjectUrl(`/registrations/${encodeURIComponent(id)}/file?inline=true`);
        setPreviewUrl(url);
      } catch (caught) {
        toast.error(extractErrorMessage(caught));
        setPreviewOpen(false);
      } finally {
        setPreviewLoading(false);
      }
    } else {
      await downloadOriginal();
    }
  };

  const downloadOriginal = async () => {
    setDownloadBusy(true);
    try {
      await downloadResponse(`/registrations/${encodeURIComponent(id)}/file`, registration.file_name);
      toast.success("Encrypted original decrypted for download");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setDownloadBusy(false);
    }
  };

  const downloadCertificate = async () => {
    try {
      await downloadResponse(`/registrations/${encodeURIComponent(id)}/certificate`, `AUTHENTIQ-${registration.registration_id}.pdf`);
      toast.success("Certificate downloaded");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const downloadPacket = async () => {
    setPacketBusy(true);
    try {
      await downloadResponse(
        `/registrations/${encodeURIComponent(id)}/evidence-packet`,
        `AUTHENTIQ-${registration.registration_id}-evidence.zip`,
      );
      toast.success("Evidence packet downloaded");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setPacketBusy(false);
    }
  };

  const revealVerificationKey = async () => {
    if (!isOwner) {
      toast.error("Only the recorded owner can reveal the private verification key");
      return;
    }
    if (verificationKey) {
      setVerificationKey(null);
      return;
    }
    setVerificationKeyBusy(true);
    try {
      const response = await api.get<{ verification_key: string }>(
        `/registrations/${encodeURIComponent(registration.id)}/verification-key`,
      );
      setVerificationKey(response.verification_key);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setVerificationKeyBusy(false);
    }
  };

  const uploadVersion = async () => {
    if (!versionFile) {
      toast.error("Select the new version file");
      return;
    }
    setVersionBusy(true);
    try {
      const uploaded = await uploadFileChunked(versionFile, setVersionProgress);
      await api.post("/versions", {
        registration_id: registration.id,
        upload_id: uploaded.upload.upload_id,
        change_description: versionNote.trim() || undefined,
      });
      toast.success("New version recorded with a real fingerprint");
      setVersionOpen(false);
      setVersionFile(null);
      setVersionNote("");
      setVersionProgress(null);
      versionsQuery.refetch();
      registrationQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setVersionBusy(false);
    }
  };

  const createShare = async () => {
    setShareBusy(true);
    try {
      const response = await api.post<ShareCreateResponse>("/sharing/create", {
        registration_id: registration.id,
        expires_in_hours: Number(shareHours),
        max_uses: Number(shareUses),
        message: shareMessage.trim() || undefined,
        disclosure,
      });
      setCreatedShare(response);
      sharesQuery.refetch();
      toast.success("Silent verification link created");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setShareBusy(false);
    }
  };

  const revokeShare = async (verificationId: string) => {
    try {
      await api.delete(`/sharing/${verificationId}`);
      toast.success("Verification link revoked");
      sharesQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const createTransfer = async () => {
    setTransferBusy(true);
    try {
      await api.post("/transfers", {
        registration_id: registration.id,
        recipient_email: transferEmail.trim(),
        reason: transferReason.trim() || undefined,
      });
      toast.success("Transfer proposal created. The recipient must accept, then you confirm.");
      setTransferOpen(false);
      setTransferEmail("");
      setTransferReason("");
      transfersQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setTransferBusy(false);
    }
  };

  const createDispute = async () => {
    setDisputeBusy(true);
    try {
      const response = await api.post<{ dispute_ref: string }>("/disputes", {
        registration_id: registration.id,
        reason: disputeReason.trim(),
        description: disputeDescription.trim(),
      });
      toast.success(`Dispute ${response.dispute_ref} opened`);
      setDisputeOpen(false);
      setDisputeReason("");
      setDisputeDescription("");
      queryClient.invalidateQueries({ queryKey: ["disputes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setDisputeBusy(false);
    }
  };

  const openPreview = () => {
    preview();
  };

  const ledger = verificationQuery.data?.ledger_record;
  const isImage = registration.mime_type.startsWith("image/");
  const isPdf = registration.mime_type === "application/pdf";
  const isText = registration.mime_type.startsWith("text/");

  return (
    <div className="space-y-5">
      <button type="button" onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-3.5" /> Back to timeline
      </button>

      <PageHeader
        eyebrow={registration.registration_id}
        title={registration.title}
        description={registration.description || "No description was attached to this record."}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={openPreview} loading={downloadBusy || previewLoading}>
              <Eye /> Preview
            </Button>
            <Button variant="outline" size="sm" onClick={downloadOriginal}>
              <Download /> Original
            </Button>
            <Button variant="outline" size="sm" onClick={downloadPacket} loading={packetBusy}>
              <Archive /> Evidence packet
            </Button>
            <Button variant="gradient" size="sm" onClick={downloadCertificate}>
              <Award /> Certificate
            </Button>
            <Button variant="ghost" size="icon" onClick={refresh} aria-label="Refresh record">
              <RefreshCw />
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={registration.status} />
        <LedgerBadge mode={registration.ledger_mode} />
        <Badge variant="outline">{titleCase(registration.asset_type)}</Badge>
        <Badge variant="outline">{titleCase(registration.privacy)}</Badge>
        {registration.team_name && (
          <Badge variant="violet">
            <Users className="size-3" /> {registration.team_name}
          </Badge>
        )}
        {registration.tags.map((tag) => (
          <Badge key={tag} variant="secondary">{tag}</Badge>
        ))}
        <span className="text-[11px] text-muted-foreground">
          {formatBytes(registration.file_size)} · {registration.file_name} · created {relativeTime(registration.registered_at)}
        </span>
      </div>

      {registration.ledger_mode === "simulation" && (
        <Alert variant="warning">
          <AlertDescription>
            Ledger transaction <span className="font-mono">{registration.ledger_tx_id || "pending"}</span> is a local simulation record. No public blockchain transaction is claimed.
          </AlertDescription>
        </Alert>
      )}

      {duplicateAlerts.length > 0 && (
        <Alert variant="info">
          <AlertDescription>
            <strong className="flex items-center gap-2 text-xs font-semibold">
              <CopyCheck className="size-4" />
              This file is already registered
            </strong>
            <span className="mt-1 block text-[11px] leading-relaxed">
              {duplicateAlerts.length} duplicate indicator(s) link this record to another registration with the same or a very similar fingerprint. The earlier timestamp keeps priority. Review the alert before taking any action.
            </span>
            <span className="mt-2 flex flex-wrap gap-2">
              {duplicateAlerts.map((alert) => (
                <Badge key={alert.id} variant="green">
                  {alert.alert_type === "exact_duplicate" ? "Identical fingerprint" : "Similar content"} ·{" "}
                  {alert.matched_label || alert.registration_label}
                </Badge>
              ))}
            </span>
            <Link to="/alerts" className="mt-2 inline-block text-[11px] font-medium underline underline-offset-4">
              Review alerts
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {pendingTransfer && (
        <Alert variant="warning">
          <AlertDescription>
            <strong className="flex items-center gap-2 text-xs font-semibold">
              <ArrowLeftRight className="size-4" />
              Ownership transfer pending
            </strong>
            <span className="mt-1 block text-[11px] leading-relaxed">
              {pendingTransfer.from_name || "The current owner"} proposed handing this creation to{" "}
              <span className="font-semibold">{pendingTransfer.to_email}</span>.{" "}
              {pendingTransfer.awaiting === "owner_confirmation"
                ? "You accepted. The current owner still has to confirm the handover before it becomes your ownership."
                : "The recipient still has to accept the handover. You keep full ownership until then."}
            </span>
            <span className="mt-2 block text-[11px] leading-relaxed">
              You already have read access to the full record, the encrypted original, and every proof. Owner-only
              actions stay locked until the transfer is confirmed.
            </span>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="overview">
        <TabsList className="h-auto flex-wrap">
          <TabsTrigger value="overview"><Fingerprint /> Overview</TabsTrigger>
          <TabsTrigger value="versions"><Layers /> Versions ({versionsQuery.data?.items.length || 1})</TabsTrigger>
          <TabsTrigger value="proofs"><ShieldCheck /> Proofs & sharing</TabsTrigger>
          <TabsTrigger value="provenance"><Sparkles /> Provenance</TabsTrigger>
          <TabsTrigger value="actions"><ArrowLeftRight /> Ownership actions</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Cryptographic identity</CardTitle>
                <CardDescription>Fingerprint and commitment values recorded on this creation.</CardDescription>
              </CardHeader>
              <CardContent>
                <InfoRow label="Registration reference" mono>{registration.registration_id}</InfoRow>
                <InfoRow label="SHA-256 fingerprint" mono><HashValue value={registration.sha256} label="SHA-256" head={18} tail={12} /></InfoRow>
                <InfoRow label="Poseidon commitment" mono><HashValue value={registration.poseidon_commitment} label="Poseidon commitment" head={18} tail={12} /></InfoRow>
                <InfoRow label="Pedersen commitment" mono><HashValue value={registration.commitment} label="Pedersen commitment" head={18} tail={12} /></InfoRow>
                <InfoRow label="Ledger transaction" mono><HashValue value={registration.ledger_tx_id} label="Ledger transaction" head={16} tail={10} /></InfoRow>
                <InfoRow label="Registered at">{formatDate(registration.registered_at)}</InfoRow>
                <InfoRow label="Creation timestamp">{formatDate(registration.creation_timestamp)}</InfoRow>
                <InfoRow label="Owner">{registration.owner_name || "You"}</InfoRow>
                <InfoRow label="File">{registration.file_name} · {formatBytes(registration.file_size)}</InfoRow>
                {registration.metadata && (
                  <>
                    <InfoRow label="Chunks">{registration.metadata.chunk_count}</InfoRow>
                    <InfoRow label="MIME type">{registration.metadata.mime_type}</InfoRow>
                  </>
                )}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Ownership trust</CardTitle>
                  <CardDescription>Recomputed from the ledger, proofs, stored bytes, and open disputes.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <OwnershipDna
                      value={registration.sha256}
                      size={104}
                      label="Ownership DNA"
                      downloadName={`AUTHENTIQ-${registration.registration_id}-dna.svg`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <ScoreRing score={trustQuery.data?.score ?? 0} />
                        <div>
                          <p className="text-xs font-semibold capitalize">{trustQuery.data?.grade || "Checking"}</p>
                          <p className="text-[11px] leading-relaxed text-muted-foreground">
                            {trustQuery.data?.summary || "Recomputing evidence."}
                          </p>
                        </div>
                      </div>
                      <div className="mt-2 space-y-1">
                        {trustQuery.data?.factors.map((factor) => (
                          <div key={factor.key} className="flex items-start justify-between gap-2 text-[10px]">
                            <span className="text-muted-foreground">{factor.label}</span>
                            <span className="font-mono font-semibold">
                              {factor.points > 0 ? "+" : ""}
                              {factor.points}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 text-[10px] leading-relaxed text-muted-foreground">
                    The DNA grid is derived deterministically from the SHA-256 fingerprint. The score is an explainable
                    evidence indicator, not a legal finding of ownership.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <KeyRound className="size-4" /> Private verification key
                  </CardTitle>
                  <CardDescription>The credential for anonymous, login-free ownership proofs.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {verificationKey ? (
                    <>
                      <div className="break-all rounded-lg border border-foreground/20 bg-accent/10 p-3 font-mono text-[10px] leading-relaxed">
                        {verificationKey}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(verificationKey);
                            toast.success("Private verification key copied");
                          }}
                        >
                          <CopyCheck /> Copy
                        </Button>
                      </div>
                    </>
                  ) : (
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      Reveal the key only on a trusted device. Treat it like a password: whoever holds it can prove
                      ownership of this registration, but it cannot decrypt the original file.
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant={verificationKey ? "ghost" : "outline"}
                      onClick={revealVerificationKey}
                      loading={verificationKeyBusy}
                      disabled={!isOwner}
                    >
                      <KeyRound /> {verificationKey ? "Hide key" : "Reveal key"}
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/verify?registration=${encodeURIComponent(registration.registration_id)}`}>
                        Public verifier <ArrowRight />
                      </Link>
                    </Button>
                  </div>
                  {!isOwner && (
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      The private credential stays with the recorded owner until a handover is confirmed. When ownership
                      moves, the credential is rotated and the new owner receives a fresh key.
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Ledger integrity</CardTitle>
                  <CardDescription>Server-side verification of the append-only record.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {verificationQuery.isLoading && <LoadingBlock rows={3} />}
                  {verificationQuery.data ? (
                    <>
                      <div className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                        <div>
                          <p className="text-xs font-medium">Ledger mode</p>
                          <p className="text-[11px] text-muted-foreground">{titleCase(verificationQuery.data.ledger_mode)}</p>
                        </div>
                        <LedgerBadge mode={verificationQuery.data.ledger_mode} />
                      </div>
                      <div className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                        <div>
                          <p className="text-xs font-medium">Record lookup</p>
                          <p className="text-[11px] text-muted-foreground">{ledger ? "Transaction found in ledger file" : "No raw ledger record"}</p>
                        </div>
                        <Badge variant={ledger ? "green" : "amber"}>{ledger ? "Found" : "Unavailable"}</Badge>
                      </div>
                      <div className="flex items-center justify-between rounded-lg border border-border/60 p-3">
                        <div>
                          <p className="text-xs font-medium">Stored proofs</p>
                          <p className="text-[11px] text-muted-foreground">{verificationQuery.data.proofs.length} proof attempt(s)</p>
                        </div>
                        <Badge variant="outline">{verificationQuery.data.proofs.filter((proof) => proof.status === "verified").length} valid</Badge>
                      </div>
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">Verification state is unavailable.</p>
                  )}
                  {ledger && (
                    <div className="rounded-lg border border-border/60 bg-background/30 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Raw record</p>
                      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all font-mono text-[10px] text-muted-foreground">
                        {JSON.stringify(ledger, null, 2)}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ArrowLeftRight className="size-4" /> Ownership chain
                  </CardTitle>
                  <CardDescription>Append-only history. A completed handover moves the recorded owner and rotates the private credential.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 bg-background/40 p-3">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current owner</p>
                      <p className="text-xs font-medium">{ownership?.current_owner_name || registration.owner_name || "Unknown"}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {ownership?.credential_rotations ? (
                        <Badge variant="violet">Credential rotated x{ownership.credential_rotations}</Badge>
                      ) : null}
                      <Badge variant={isOwner ? "green" : pendingTransfer ? "amber" : "outline"}>
                        {isOwner ? "You own this" : pendingTransfer ? "Pending handover" : "Read access"}
                      </Badge>
                    </div>
                  </div>

                  {ownershipChainQuery.data?.events?.length ? (
                    ownershipChainQuery.data.events.map((event, index) => (
                      <div key={event.id || `event-${index}`} className="rounded-lg border border-border/60 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium">
                            {event.kind === "registered"
                              ? `Registered by ${event.owner_name || "creator"}`
                              : `${event.from_name || "Owner"} → ${event.to_name || event.to_email || "Recipient"}`}
                          </p>
                          <StatusBadge status={event.status} />
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {event.kind === "registered"
                            ? `${formatDate(event.at)}${event.ledger_tx_id ? " · committed to the ledger" : ""}`
                            : `Proposed ${formatDate(event.created_at)}${event.completed_at ? ` · completed ${formatDate(event.completed_at)}` : ""}${event.reason ? ` · “${event.reason}”` : ""}`}
                        </p>
                        {event.ledger_tx_id && (
                          <div className="mt-2">
                            <HashValue value={event.ledger_tx_id} label="Ledger transaction" head={14} tail={10} />
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">No ownership transfers have been proposed for this record.</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Fingerprint className="size-4" /> File data
                  </CardTitle>
                  <CardDescription>Everything recorded for the stored original of this creation.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {registration.file ? (
                    <>
                      <InfoRow label="Original name" mono>{registration.file.original_name}</InfoRow>
                      <InfoRow label="MIME type">{registration.file.mime_type}</InfoRow>
                      <InfoRow label="Extension">{registration.file.extension || "—"}</InfoRow>
                      <InfoRow label="Size">{formatBytes(registration.file.size_bytes)}</InfoRow>
                      <InfoRow label="Encrypted size">{formatBytes(registration.file.encrypted_size_bytes)}</InfoRow>
                      <InfoRow label="Chunks">{registration.file.chunk_count}</InfoRow>
                      <InfoRow label="Perceptual hash" mono>
                        {registration.file.perceptual_hash ? (
                          <HashValue value={registration.file.perceptual_hash} label="Perceptual hash" head={16} tail={10} />
                        ) : (
                          "Not applicable for this asset type"
                        )}
                      </InfoRow>
                      <InfoRow label="Stored bytes">{registration.file.stored ? "Present and decryptable" : "Missing from storage"}</InfoRow>
                      {registration.file.extracted_text ? (
                        <div className="mt-2 rounded-lg border border-border/60 bg-background/40 p-3">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Extracted text</p>
                          <pre className="mt-1.5 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-relaxed text-muted-foreground">
                            {registration.file.extracted_text}
                          </pre>
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">File metadata is unavailable for this record.</p>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="versions" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">Creative version history</h3>
              <p className="text-xs text-muted-foreground">Each version gets its own SHA-256 fingerprint and ledger event. The original commitment is preserved.</p>
            </div>
            <Button size="sm" onClick={() => setVersionOpen(true)} disabled={!isOwner}>
              <Upload /> Add version
            </Button>
          </div>

          {versionsQuery.isLoading && <LoadingBlock rows={4} />}
          <div className="space-y-2">
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="blue">Version {registration.version === 1 ? 1 : 1}</Badge>
                  <span className="text-xs font-medium">{registration.file_name}</span>
                </div>
                <span className="text-[10px] text-muted-foreground">Original · {formatDate(registration.registered_at)}</span>
              </div>
              <div className="mt-2"><HashValue value={registration.sha256} label="Original fingerprint" head={18} tail={12} /></div>
            </div>
            {versionsQuery.data?.items.map((version) => (
              <div key={version.id} className="rounded-xl border border-border/70 bg-card/60 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">Version {version.version_no}</Badge>
                      <span className="text-xs font-medium">{version.file_name}</span>
                      <span className="text-[10px] text-muted-foreground">{formatBytes(version.file_size)}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {version.contributor_name || "Contributor"} · {formatDate(version.created_at)} · {version.change_description || "No change description"}
                    </p>
                    <div className="mt-2"><HashValue value={version.sha256} label="Version fingerprint" head={18} tail={12} /></div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        downloadResponse(`/versions/${version.id}/file`, version.file_name)
                          .then(() => toast.success("Version downloaded"))
                          .catch((caught) => toast.error(extractErrorMessage(caught)))
                      }
                    >
                      <Download /> File
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        downloadResponse(`/versions/${version.id}/certificate`, `AUTHENTIQ-${registration.registration_id}-V${version.version_no}.pdf`)
                          .then(() => toast.success("Version certificate downloaded"))
                          .catch((caught) => toast.error(extractErrorMessage(caught)))
                      }
                    >
                      <Award /> Certificate
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {!!versionsQuery.data?.items.length && (
            <Card>
              <CardHeader>
                <CardTitle>Compare versions</CardTitle>
                <CardDescription>Fingerprints are compared server-side; no fabricated diff is shown.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={leftVersion} onChange={(event) => setLeftVersion(event.target.value)} aria-label="Left version">
                    <option value="">Select first version</option>
                    {versionsQuery.data.items.map((version) => (
                      <option key={version.id} value={version.id}>Version {version.version_no} · {version.file_name}</option>
                    ))}
                  </Select>
                  <Select value={rightVersion} onChange={(event) => setRightVersion(event.target.value)} aria-label="Right version">
                    <option value="">Select second version</option>
                    {versionsQuery.data.items.map((version) => (
                      <option key={version.id} value={version.id}>Version {version.version_no} · {version.file_name}</option>
                    ))}
                  </Select>
                </div>
                {leftVersion === rightVersion && leftVersion && <p className="text-xs text-foreground">Select two different versions.</p>}
                {compareQuery.data && (
                  <div className="rounded-lg border border-border/60 p-3">
                    <div className="flex items-center gap-2">
                      <GitCompareArrows className="size-4 text-foreground" />
                      <span className="text-xs font-medium">
                        {compareQuery.data.same_fingerprint ? "Fingerprints are identical" : "Fingerprints differ"}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-1 text-[11px] text-muted-foreground sm:grid-cols-2">
                      {Object.entries(compareQuery.data.differences).map(([field, differs]) => (
                        <span key={field}>{titleCase(field)}: {differs ? "changed" : "unchanged"}</span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="proofs" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Zero-knowledge proof status</CardTitle>
                <CardDescription>Every proof attempt is stored. Validity is decided by the server verifier.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {proofsQuery.data?.items.length ? (
                  proofsQuery.data.items.map((proof) => (
                    <div key={proof.id} className="rounded-lg border border-border/60 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <StatusBadge status={proof.status} />
                        <span className="text-[10px] text-muted-foreground">{formatDate(proof.created_at)}</span>
                      </div>
                      <p className="mt-1.5 text-[11px] text-muted-foreground">{proof.scheme}</p>
                      {proof.verified_at && <p className="text-[11px] text-foreground">Verified {relativeTime(proof.verified_at)}</p>}
                    </div>
                  ))
                ) : (
                  <EmptyState
                    title="No proofs generated"
                    description="A proof requires a fresh one-time challenge and a local file fingerprint match."
                    icon={<ShieldCheck className="size-5" />}
                    className="border-0 py-8"
                    action={
                      <Button asChild size="sm">
                        <Link to={`/anonymous-verification?registration=${encodeURIComponent(registration.registration_id)}`}>Prove possession</Link>
                      </Button>
                    }
                  />
                )}
                <Button asChild variant="outline" className="w-full">
                  <Link to={`/anonymous-verification?registration=${encodeURIComponent(registration.registration_id)}`}>
                    <ShieldCheck /> Open verification workspace
                  </Link>
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-start justify-between gap-2">
                <div>
                  <CardTitle>Silent sharing links</CardTitle>
                  <CardDescription>Share a proof, not the file. Each link is expiring and usage-limited.</CardDescription>
                </div>
                <Button size="sm" onClick={() => { setCreatedShare(null); setShareOpen(true); }}>
                  <Link2 /> Create
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {relevantShares.length ? (
                  relevantShares.map((share) => (
                    <div key={share.id} className="rounded-lg border border-border/60 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <StatusBadge status={share.status} />
                        <span className="text-[10px] text-muted-foreground">{share.uses}/{share.max_uses} uses</span>
                      </div>
                      <p className="mt-1.5 break-all font-mono text-[10px] text-muted-foreground">
                        {`${window.location.origin}/verify/${share.verification_id}`}
                      </p>
                      <p className="mt-1 text-[10px] text-muted-foreground">Expires {formatDate(share.expires_at)}</p>
                      <div className="mt-2 flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(`${window.location.origin}/verify/${share.verification_id}`);
                            toast.success("Verification link copied");
                          }}
                        >
                          Copy link
                        </Button>
                        {share.status !== "revoked" && (
                          <ConfirmDialog
                            trigger={<Button size="sm" variant="ghost" className="text-destructive"><Trash2 /> Revoke</Button>}
                            title="Revoke this verification link?"
                            description="The public verifier will immediately receive a revoked response. Existing screenshots remain outside AUTHENTIQ's control."
                            confirmLabel="Revoke link"
                            destructive
                            onConfirm={() => revokeShare(share.verification_id)}
                          />
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="py-6 text-center text-xs text-muted-foreground">No silent sharing links exist for this record.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Alert variant="info">
            <AlertDescription>
              The default sigma proof proves knowledge of the commitment opening. The registration fingerprint is checked separately against the local file and the server record; hash equality is not enforced inside the circuit.
            </AlertDescription>
          </Alert>
        </TabsContent>

        <TabsContent value="provenance" className="space-y-4">
          <Card>
            <CardHeader className="flex-row items-start justify-between gap-2">
              <div>
                <CardTitle>AI provenance declarations</CardTitle>
                <CardDescription>Self-reported declarations recorded with your identity. Detection is probabilistic and never fabricated.</CardDescription>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link to={`/provenance?registration=${encodeURIComponent(registration.registration_id)}`}>
                  <PlusCircle /> Add declaration
                </Link>
              </Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {provenanceQuery.data?.items.length ? (
                provenanceQuery.data.items.map((record) => (
                  <div key={record.id} className="rounded-lg border border-border/60 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <Badge variant={record.declared_ai ? "violet" : "green"}>{record.declared_ai ? "AI declared" : "No AI declared"}</Badge>
                      <span className="text-[10px] text-muted-foreground">{formatDate(record.created_at)}</span>
                    </div>
                    {record.declared_ai && (
                      <p className="mt-1.5 text-xs text-muted-foreground">
                        {[record.model_name, record.tool_name].filter(Boolean).join(" · ") || "Model or tool not specified"}
                      </p>
                    )}
                    {record.human_contribution && <p className="mt-1.5 text-[11px] text-muted-foreground">{record.human_contribution}</p>}
                    {record.editing_details && <p className="mt-1 text-[11px] text-muted-foreground">{record.editing_details}</p>}
                    {record.prompt_commitment && <p className="mt-1 break-all font-mono text-[10px] text-muted-foreground">{record.prompt_commitment}</p>}
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={record.analysis_available ? "blue" : "slate"}>{record.analysis_available ? "Metadata analysis available" : "No analysis output"}</Badge>
                      {record.ledger_tx_id && <HashValue value={record.ledger_tx_id} label="Ledger transaction" head={10} tail={8} />}
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No provenance records"
                  description="Record an honest AI or human provenance declaration for this creation."
                  icon={<Sparkles className="size-5" />}
                  className="border-0 py-8"
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="actions" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-accent/15 text-foreground"><ShieldCheck className="size-4" /></div>
                <CardTitle>Prove ownership</CardTitle>
                <CardDescription>Generate a real BN254 Schnorr proof after selecting the original file.</CardDescription>
              </CardHeader>
              <CardContent>
                {isOwner ? (
                  <Button asChild className="w-full" variant="outline">
                    <Link to={`/anonymous-verification?registration=${encodeURIComponent(registration.registration_id)}`}>
                      Open verification <ArrowRight />
                    </Link>
                  </Button>
                ) : (
                  <Button className="w-full" variant="outline" disabled>
                    <Lock /> Ownership pending
                  </Button>
                )}
                {!isOwner && (
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                    Generating a proof from the workspace needs the ownership credential, so it unlocks when the handover
                    is confirmed.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-accent/15 text-foreground"><Link2 className="size-4" /></div>
                <CardTitle>Silent share</CardTitle>
                <CardDescription>Create a privacy-preserving verification link with explicit disclosure controls.</CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" onClick={() => { setCreatedShare(null); setShareOpen(true); }} disabled={!isOwner}>
                  Create link
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-secondary text-foreground"><ArrowLeftRight className="size-4" /></div>
                <CardTitle>Transfer ownership</CardTitle>
                <CardDescription>Ownership moves only after the recipient accepts and you confirm. The chain is append-only.</CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" onClick={() => setTransferOpen(true)} disabled={!isOwner}>
                  Propose transfer
                </Button>
                {!isOwner && (
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                    Only the recorded owner can hand this creation over to someone else.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-foreground/5 text-destructive"><Gavel className="size-4" /></div>
                <CardTitle>Open a dispute</CardTitle>
                <CardDescription>Submit a claim for review with an evidence report and audit trail.</CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" onClick={() => setDisputeOpen(true)}>
                  Submit dispute
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-accent/25 text-foreground"><Users className="size-4" /></div>
                <CardTitle>{registration.team ? registration.team.name : "Team ownership"}</CardTitle>
                <CardDescription>
                  {registration.team
                    ? "This record is attributed to a team workspace. Every active member can open it."
                    : "Agree on a 100% ownership split with unanimous member approval."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {registration.team ? (
                  <>
                    <div className="space-y-1.5">
                      {registration.team.members.map((member) => (
                        <div key={member.id} className="flex items-center justify-between gap-2 text-[11px]">
                          <span className="truncate text-muted-foreground">{member.name}</span>
                          <span className="font-medium">{member.percent}%</span>
                        </div>
                      ))}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {registration.team.allocation_status ? (
                        <Badge variant={registration.team.allocation_status === "approved" ? "green" : "amber"}>
                          Split {registration.team.allocation_status} · {registration.team.allocation_total}%
                        </Badge>
                      ) : (
                        <Badge variant="slate">No split proposed yet</Badge>
                      )}
                      {registration.team_membership && (
                        <Badge variant="outline">
                          Your role: {titleCase(registration.team_membership.role)}
                          {registration.team_membership.percent ? ` · ${registration.team_membership.percent}%` : ""}
                        </Badge>
                      )}
                    </div>
                    <Button asChild className="w-full" variant="outline">
                      <Link to={`/teams/${registration.team.id}`}>Open team workspace</Link>
                    </Button>
                  </>
                ) : (
                  <Button asChild className="w-full" variant="outline">
                    <Link to="/teams">Open teams</Link>
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-lg bg-slate-500/10 text-muted-foreground"><Lock className="size-4" /></div>
                <CardTitle>Encrypted storage</CardTitle>
                <CardDescription>Original bytes are decrypted only for authorized downloads and never included in certificates.</CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full" variant="outline" onClick={downloadOriginal} loading={downloadBusy}>
                  <Download /> Download encrypted original
                </Button>
              </CardContent>
            </Card>
          </div>

          <Alert variant="info">
            <AlertDescription>
              Ownership changes and dispute decisions are written to the audit chain. AUTHENTIQ records evidence; it does not make legal ownership determinations.
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      <Dialog open={previewOpen} onOpenChange={(open) => { setPreviewOpen(open); if (!open && previewUrl) { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); } }}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{registration.file_name}</DialogTitle>
            <DialogDescription>Decrypted inline for your authorized session. Fingerprint: {registration.sha256.slice(0, 24)}...</DialogDescription>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-auto rounded-lg border border-border bg-slate-950/50">
            {previewLoading && <div className="p-10 text-center text-xs text-muted-foreground">Decrypting preview...</div>}
            {!previewLoading && previewUrl && isImage && <img src={previewUrl} alt={registration.title} className="mx-auto max-h-[68vh] object-contain" />}
            {!previewLoading && previewUrl && isPdf && <iframe title="PDF preview" src={previewUrl} className="h-[68vh] w-full" />}
            {!previewLoading && previewUrl && isText && (
              <iframe title="Text preview" src={previewUrl} className="h-[68vh] w-full bg-white" />
            )}
            {!previewLoading && !previewUrl && <div className="p-10 text-center text-xs text-muted-foreground">Preview unavailable.</div>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={downloadOriginal}><Download /> Download</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={versionOpen} onOpenChange={(open) => { if (!versionBusy) { setVersionOpen(open); if (!open) { setVersionProgress(null); setVersionFile(null); setVersionNote(""); } } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record a new version</DialogTitle>
            <DialogDescription>The new file receives a new SHA-256 fingerprint and a parent-linked version event. The original commitment stays intact.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <FileDropzone file={versionFile} onFileChange={setVersionFile} disabled={versionBusy} hint="Upload the revised file. It is verified and encrypted with the same pipeline." />
            <Field label="Change description" htmlFor="version-note" hint="Optional">
              <Textarea id="version-note" value={versionNote} onChange={(event) => setVersionNote(event.target.value)} placeholder="What changed in this version?" disabled={versionBusy} />
            </Field>
            {versionProgress && (
              <div className="rounded-lg border border-foreground/20 bg-blue-500/5 p-3">
                <div className="flex justify-between text-[11px]"><span>{titleCase(versionProgress.phase)}</span><span>{versionProgress.percent}%</span></div>
                <Progress value={versionProgress.percent} className="my-2" />
                <p className="text-[11px] text-muted-foreground">{versionProgress.message}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVersionOpen(false)} disabled={versionBusy}>Cancel</Button>
            <Button onClick={uploadVersion} loading={versionBusy} disabled={!versionFile}>Record version</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={shareOpen} onOpenChange={(open) => { if (!shareBusy) { setShareOpen(open); if (!open) setCreatedShare(null); } }}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Create a silent verification link</DialogTitle>
            <DialogDescription>A proof package is generated now. The verifier can validate the commitment opening without receiving the file or private secret.</DialogDescription>
          </DialogHeader>
          {createdShare ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-foreground/20 bg-accent/15 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground"><CheckCircle2 className="size-4" /> Link created</div>
                <p className="mt-2 break-all font-mono text-[11px]">{`${window.location.origin}/verify/${createdShare.verification_id}`}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/verify/${createdShare.verification_id}`);
                      toast.success("Link copied");
                    }}
                  >
                    Copy link
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => navigate(`/verify/${createdShare.verification_id}`)}>
                    Open verifier view
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      const blob = new Blob([JSON.stringify(createdShare.proof_package, null, 2)], { type: "application/json" });
                      const url = URL.createObjectURL(blob);
                      const anchor = document.createElement("a");
                      anchor.href = url;
                      anchor.download = `AUTHENTIQ-${createdShare.verification_id}-proof-package.json`;
                      anchor.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Download proof package
                  </Button>
                </div>
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Expires {formatDate(createdShare.expires_at)} · maximum {createdShare.max_uses} verification{createdShare.max_uses === 1 ? "" : "s"}. Revoke it any time from this record.
              </p>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShareOpen(false)}>Close</Button>
              </DialogFooter>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Expires in hours" htmlFor="share-hours">
                    <Input id="share-hours" type="number" min={1} max={720} value={shareHours} onChange={(event) => setShareHours(event.target.value)} />
                  </Field>
                  <Field label="Maximum uses" htmlFor="share-uses">
                    <Input id="share-uses" type="number" min={1} max={100} value={shareUses} onChange={(event) => setShareUses(event.target.value)} />
                  </Field>
                </div>
                <Field label="Message to verifier" htmlFor="share-message" hint="Optional">
                  <Textarea id="share-message" value={shareMessage} onChange={(event) => setShareMessage(event.target.value)} maxLength={500} placeholder="Context for the recipient" />
                </Field>
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Disclosure controls</p>
                  <div className="space-y-2">
                    {Object.entries(disclosureLabels).map(([key, label]) => (
                      <label key={key} className="flex cursor-pointer items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          checked={disclosure[key]}
                          onChange={(event) => setDisclosure((current) => ({ ...current, [key]: event.target.checked }))}
                          className="size-4 rounded border-border accent-blue-500"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
                <Alert variant="info">
                  <AlertDescription>Only the fields selected above can appear on the public verifier page. The file itself is never exposed.</AlertDescription>
                </Alert>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShareOpen(false)} disabled={shareBusy}>Cancel</Button>
                <Button onClick={createShare} loading={shareBusy}>Create link</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={transferOpen} onOpenChange={(open) => !transferBusy && setTransferOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Propose an ownership transfer</DialogTitle>
            <DialogDescription>The recipient must have an AUTHENTIQ account and accept before you can confirm. No ownership changes on proposal.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Field label="Recipient email" htmlFor="transfer-email" required>
              <Input id="transfer-email" type="email" value={transferEmail} onChange={(event) => setTransferEmail(event.target.value)} placeholder="recipient@example.com" />
            </Field>
            <Field label="Reason" htmlFor="transfer-reason" hint="Optional">
              <Textarea id="transfer-reason" value={transferReason} onChange={(event) => setTransferReason(event.target.value)} placeholder="Why is ownership moving?" />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTransferOpen(false)} disabled={transferBusy}>Cancel</Button>
            <Button onClick={createTransfer} loading={transferBusy} disabled={!transferEmail.trim()}>Propose transfer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={disputeOpen} onOpenChange={(open) => !disputeBusy && setDisputeOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Open a dispute</DialogTitle>
            <DialogDescription>Provide a factual claim. The evidence report assembles fingerprints, ledger records, proofs, versions, and transfers for review.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Field label="Reason" htmlFor="dispute-reason" required>
              <Input id="dispute-reason" value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)} maxLength={200} placeholder="Unauthorized republication" />
            </Field>
            <Field label="Description" htmlFor="dispute-description" required hint="At least 20 characters">
              <Textarea id="dispute-description" value={disputeDescription} onChange={(event) => setDisputeDescription(event.target.value)} maxLength={8000} className="min-h-[120px]" placeholder="Describe the claim, dates, and evidence you can provide." />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisputeOpen(false)} disabled={disputeBusy}>Cancel</Button>
            <Button onClick={createDispute} loading={disputeBusy} disabled={disputeReason.trim().length < 3 || disputeDescription.trim().length < 20}>Submit dispute</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1"><FileClock className="size-3" /> Recorded {formatDate(registration.registered_at)}</span>
        <span className="flex items-center gap-1"><Fingerprint className="size-3" /> SHA-256 {percent(1)} verified upload</span>
        <span className="flex items-center gap-1"><Eye className="size-3" /> Preview is a privileged, audited action</span>
      </div>
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;
  return (
    <div className="relative flex size-[68px] shrink-0 items-center justify-center">
      <svg viewBox="0 0 64 64" className="size-[68px] -rotate-90">
        <circle cx="32" cy="32" r={radius} fill="none" stroke="#D0D0D0" strokeWidth="5" />
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
        />
      </svg>
      <span className="absolute text-sm font-semibold">{score}</span>
    </div>
  );
}
