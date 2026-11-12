import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, BrainCircuit, FileSearch, PlusCircle, Sparkles, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { Field, InfoRow } from "@/components/common/field";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, extractErrorMessage } from "@/lib/api";
import type { Paginated, ProvenanceRecord, Registration } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

interface AnalyzeResponse {
  registration_id: string;
  analysis: Record<string, unknown>;
  disclaimer: string;
}

export default function ProvenancePage() {
  const queryClient = useQueryClient();
  const [recordOpen, setRecordOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<ProvenanceRecord | null>(null);

  const [registrationId, setRegistrationId] = useState("");
  const [declaredAi, setDeclaredAi] = useState(false);
  const [modelName, setModelName] = useState("");
  const [toolName, setToolName] = useState("");
  const [promptCommitment, setPromptCommitment] = useState("");
  const [humanContribution, setHumanContribution] = useState("");
  const [editingDetails, setEditingDetails] = useState("");
  const [creationDate, setCreationDate] = useState("");

  const registrationsQuery = useQuery({
    queryKey: ["registrations", "provenance-options"],
    queryFn: () => api.get<Paginated<Registration>>("/registrations?page_size=100&sort=recent"),
  });
  const provenanceQuery = useQuery({
    queryKey: ["provenance"],
    queryFn: () => api.get<{ items: ProvenanceRecord[] }>("/provenance"),
  });

  const registrations = registrationsQuery.data?.items || [];
  const records = provenanceQuery.data?.items || [];
  const registrationMap = useMemo(() => {
    const map = new Map<string, Registration>();
    registrations.forEach((item) => map.set(item.id, item));
    return map;
  }, [registrations]);

  const openRecordDialog = (preset?: string) => {
    setRegistrationId(preset || registrations[0]?.id || "");
    setDeclaredAi(false);
    setModelName("");
    setToolName("");
    setPromptCommitment("");
    setHumanContribution("");
    setEditingDetails("");
    setCreationDate("");
    setRecordOpen(true);
  };

  const recordProvenance = async () => {
    if (!registrationId) return;
    setBusy(true);
    try {
      await api.post<ProvenanceRecord>("/provenance/record", {
        registration_id: registrationId,
        declared_ai: declaredAi,
        model_name: declaredAi ? modelName.trim() || null : null,
        tool_name: toolName.trim() || null,
        prompt_commitment: promptCommitment.trim() || null,
        human_contribution: humanContribution.trim() || null,
        editing_details: editingDetails.trim() || null,
        creation_date: creationDate ? new Date(creationDate).toISOString() : null,
      });
      toast.success("Provenance record written to the ledger");
      setRecordOpen(false);
      provenanceQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const runAnalysis = async (id: string) => {
    setAnalysisBusy(true);
    setAnalysisOpen(true);
    setAnalysis(null);
    try {
      const response = await api.post<AnalyzeResponse>("/provenance/analyze", { registration_id: id });
      setAnalysis(response);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
      setAnalysisOpen(false);
    } finally {
      setAnalysisBusy(false);
    }
  };

  const declaredCount = records.filter((record) => record.declared_ai).length;
  const analyzedCount = records.filter((record) => record.analysis_available).length;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="AI provenance"
        title="Record how a work was made"
        description="Declare AI involvement, commit to prompts, and attach the model or tool used. Declarations are recorded with your identity; optional analysis only reports signals that were actually inspected."
        actions={
          <Button variant="gradient" size="sm" onClick={() => openRecordDialog()} disabled={!registrations.length}>
            <PlusCircle /> Add provenance
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Provenance records</p>
          <p className="mt-2 text-2xl font-semibold">{records.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">AI involvement declared</p>
          <p className="mt-2 text-2xl font-semibold">{declaredCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Analysis available</p>
          <p className="mt-2 text-2xl font-semibold">{analyzedCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Registered creations</p>
          <p className="mt-2 text-2xl font-semibold">{registrations.length}</p>
        </Card>
      </div>

      <Alert variant="info">
        <AlertDescription>
          AI-content detection is probabilistic. AUTHENTIQ stores self-reported declarations and records only the metadata signals that were inspected. No classifier result is fabricated.
        </AlertDescription>
      </Alert>

      {provenanceQuery.isLoading && <LoadingBlock rows={5} />}
      {provenanceQuery.isError && <ErrorState error={provenanceQuery.error} onRetry={() => provenanceQuery.refetch()} />}

      {!provenanceQuery.isLoading && !provenanceQuery.isError && !records.length && (
        <EmptyState
          icon={<Sparkles className="size-5" />}
          title="No provenance records yet"
          description="Attach a declaration to a registered creation. A commitment of the declaration is written to the append-only ledger while the details stay private to authorized viewers."
          action={<Button onClick={() => openRecordDialog()} disabled={!registrations.length}>Add provenance</Button>}
        />
      )}

      {!!records.length && (
        <Card>
          <CardHeader>
            <CardTitle>Provenance history</CardTitle>
            <CardDescription>Every declaration and inspection result tied to your registrations.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {records.map((record) => {
              const registration = registrationMap.get(record.registration_id);
              return (
                <button
                  key={record.id}
                  type="button"
                  onClick={() => setSelectedRecord(record)}
                  className="w-full rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-accent/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={record.declared_ai ? "violet" : "green"}>
                      {record.declared_ai ? "AI involved" : "No AI declared"}
                    </Badge>
                    {record.analysis_available && <Badge variant="blue">Analysis available</Badge>}
                    <span className="text-[11px] text-muted-foreground">Created {relativeTime(record.created_at)}</span>
                  </div>
                  <p className="mt-1.5 text-sm font-medium">
                    {registration?.title || record.registration_label || "Registration"}
                    <span className="ml-2 font-mono text-[11px] text-muted-foreground">{record.registration_label}</span>
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {record.declared_ai ? [record.model_name, record.tool_name].filter(Boolean).join(" · ") || "Declared AI involvement" : "Self-reported human-authored record"}
                    {record.creation_date ? ` · created ${formatDate(record.creation_date, "MMM d, yyyy")}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {record.ledger_tx_id ? <HashValue value={record.ledger_tx_id} label="Ledger transaction" head={14} tail={10} /> : <span className="text-[11px] text-muted-foreground">No ledger transaction</span>}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(event) => {
                        event.stopPropagation();
                        runAnalysis(record.registration_id);
                      }}
                      disabled={analysisBusy}
                    >
                      <FileSearch /> Inspect metadata
                    </Button>
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>
      )}

      {!!registrations.length && (
        <Card>
          <CardHeader>
            <CardTitle>Creations without provenance</CardTitle>
            <CardDescription>Attach a declaration to improve the ownership record. Analysis is optional.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {registrations.filter((item) => !records.some((record) => record.registration_id === item.id)).map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 p-3">
                <div className="min-w-0">
                  <Link to={`/registrations/${item.id}`} className="truncate text-sm font-medium hover:text-foreground">{item.title}</Link>
                  <p className="text-[11px] text-muted-foreground">{item.registration_id} · {titleCase(item.asset_type)} · {formatDate(item.registered_at)}</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => runAnalysis(item.id)} disabled={analysisBusy}><FileSearch /> Analyze</Button>
                  <Button size="sm" variant="outline" onClick={() => openRecordDialog(item.id)}><PlusCircle /> Declare</Button>
                </div>
              </div>
            ))}
            {registrations.every((item) => records.some((record) => record.registration_id === item.id)) && (
              <p className="py-3 text-center text-xs text-muted-foreground">Every registration has at least one provenance entry.</p>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog open={recordOpen} onOpenChange={(value) => !busy && setRecordOpen(value)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Record AI provenance</DialogTitle>
            <DialogDescription>
              The declaration is encrypted at rest. A commitment and ledger entry are created so the statement can be referenced later.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Field label="Registered creation" htmlFor="provenance-registration" required>
              <Select id="provenance-registration" value={registrationId} onChange={(event) => setRegistrationId(event.target.value)}>
                {registrations.map((item) => (
                  <option key={item.id} value={item.id}>{item.title} · {item.registration_id}</option>
                ))}
              </Select>
            </Field>
            <div className="flex items-center justify-between rounded-lg border border-border/60 p-3">
              <div>
                <p className="text-sm font-medium">This work involved generative AI</p>
                <p className="text-[11px] text-muted-foreground">Declaring AI involvement is recorded honestly and is not penalized.</p>
              </div>
              <Switch checked={declaredAi} onChange={(event) => setDeclaredAi(event.target.checked)} aria-label="Declare AI involvement" />
            </div>
            {declaredAi && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Model name" htmlFor="provenance-model" hint="Required if no tool is given">
                  <Input id="provenance-model" value={modelName} onChange={(event) => setModelName(event.target.value)} placeholder="e.g. Stable Diffusion XL" />
                </Field>
                <Field label="Tool or platform" htmlFor="provenance-tool">
                  <Input id="provenance-tool" value={toolName} onChange={(event) => setToolName(event.target.value)} placeholder="e.g. ComfyUI, Photoshop" />
                </Field>
              </div>
            )}
            <Field label="Prompt commitment" htmlFor="provenance-prompt" hint="The raw prompt is never stored by this field">
              <Textarea id="provenance-prompt" value={promptCommitment} onChange={(event) => setPromptCommitment(event.target.value)} className="min-h-[80px]" placeholder="Paste a prompt to commit to it, or leave blank." />
            </Field>
            <Field label="Human contribution" htmlFor="provenance-human">
              <Textarea id="provenance-human" value={humanContribution} onChange={(event) => setHumanContribution(event.target.value)} className="min-h-[80px]" placeholder="Describe composition, editing, direction, or other human input." />
            </Field>
            <Field label="Editing details" htmlFor="provenance-editing">
              <Textarea id="provenance-editing" value={editingDetails} onChange={(event) => setEditingDetails(event.target.value)} className="min-h-[70px]" placeholder="Post-processing, retouching, or assembly steps." />
            </Field>
            <Field label="Creation date" htmlFor="provenance-date" hint="Optional">
              <Input id="provenance-date" type="datetime-local" value={creationDate} onChange={(event) => setCreationDate(event.target.value)} />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRecordOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={recordProvenance} loading={busy} disabled={!registrationId || (declaredAi && !modelName.trim() && !toolName.trim())}>
              <BrainCircuit /> Record provenance
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={analysisOpen} onOpenChange={setAnalysisOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Metadata inspection</DialogTitle>
            <DialogDescription>Only signals the backend actually inspected are shown. This is not a definitive AI detector.</DialogDescription>
          </DialogHeader>
          {analysisBusy && <p className="py-8 text-center text-xs text-muted-foreground">Inspecting metadata...</p>}
          {analysis && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="blue">{analysis.registration_id}</Badge>
                <Badge variant={Boolean((analysis.analysis as any)?.analysis_available) ? "green" : "slate"}>
                  {(analysis.analysis as any)?.analysis_available ? "Analysis available" : "No supported signals"}
                </Badge>
              </div>
              <pre className="max-h-[50vh] overflow-auto rounded-lg border border-border/60 bg-background/50 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
{JSON.stringify(analysis.analysis, null, 2)}
              </pre>
              <Alert variant="warning"><AlertDescription>{analysis.disclaimer}</AlertDescription></Alert>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!selectedRecord} onOpenChange={(value) => !value && setSelectedRecord(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Provenance record</DialogTitle>
            <DialogDescription>{selectedRecord?.registration_label} · recorded {formatDate(selectedRecord?.created_at)}</DialogDescription>
          </DialogHeader>
          {selectedRecord && (
            <div className="space-y-1">
              <InfoRow label="AI declared">{selectedRecord.declared_ai ? "Yes" : "No"}</InfoRow>
              <InfoRow label="Model">{selectedRecord.model_name || "Not provided"}</InfoRow>
              <InfoRow label="Tool">{selectedRecord.tool_name || "Not provided"}</InfoRow>
              <InfoRow label="Creation date">{formatDate(selectedRecord.creation_date)}</InfoRow>
              <InfoRow label="Prompt commitment" mono>{selectedRecord.prompt_commitment || "Not provided"}</InfoRow>
              <InfoRow label="Human contribution">{selectedRecord.human_contribution || "Not provided"}</InfoRow>
              <InfoRow label="Editing details">{selectedRecord.editing_details || "Not provided"}</InfoRow>
              <InfoRow label="Ledger transaction" mono>{selectedRecord.ledger_tx_id || "Not recorded"}</InfoRow>
              <InfoRow label="Analysis">{selectedRecord.analysis_available ? "Available" : "Not available"}</InfoRow>
              {selectedRecord.analysis && (
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-border/60 bg-background/50 p-3 font-mono text-[10px] text-muted-foreground">
{JSON.stringify(selectedRecord.analysis, null, 2)}
                </pre>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedRecord(null)}>Close</Button>
            {selectedRecord && (
              <Button variant="outline" onClick={() => { const id = selectedRecord.registration_id; setSelectedRecord(null); runAnalysis(id); }}>
                <Wand2 /> Run inspection
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
