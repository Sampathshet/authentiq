export interface User {
  id: string;
  email: string;
  display_name: string;
  account_type: string;
  role: string;
  organization_id: string | null;
  organization_name?: string | null;
  avatar_color: string;
  is_demo: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Registration {
  id: string;
  registration_id: string;
  title: string;
  description?: string | null;
  asset_type: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  sha256: string;
  commitment: string;
  poseidon_commitment: string;
  privacy: string;
  status: string;
  version: number;
  ledger_tx_id?: string | null;
  ledger_mode: string;
  registered_at: string;
  creation_timestamp?: string | null;
  verified_at?: string | null;
  owner_id: string;
  owner_name?: string | null;
  organization_id?: string | null;
  team_id?: string | null;
  team_name?: string | null;
  team?: TeamContext;
  team_membership?: {
    role: string;
    status: string;
    percent: number;
  } | null;
  is_demo: boolean;
  tags: string[];
  metadata?: {
    original_name: string;
    mime_type: string;
    extension: string;
    size_bytes: number;
    chunk_count: number;
    perceptual_hash?: string | null;
  };
  version_count?: number;
  proof_count?: number;
  ownership_status?: "owned" | "pending_confirmation" | "not_owner";
  pending_ownership?: boolean;
  ownership?: OwnershipState;
  file?: RegistrationFile;
}

export interface OwnershipState {
  status: "owned" | "pending_confirmation" | "not_owner";
  is_owner: boolean;
  current_owner_id: string;
  current_owner_name?: string | null;
  original_owner_id: string;
  original_owner_name?: string | null;
  previous_owner_name?: string | null;
  transfer_count: number;
  acquired_via_transfer_id?: string | null;
  acquired_at?: string | null;
  credential_rotations: number;
  credential_version: number;
  pending_transfer?: {
    id: string;
    status: string;
    from_name?: string | null;
    from_id: string;
    to_email: string;
    reason?: string | null;
    created_at: string;
    recipient_responded_at?: string | null;
    awaiting: "owner_confirmation" | "recipient_response";
  } | null;
}

export interface RegistrationFile {
  original_name: string;
  mime_type: string;
  extension: string;
  size_bytes: number;
  encrypted_size_bytes: number;
  chunk_count: number;
  perceptual_hash?: string | null;
  extracted_text?: string | null;
  stored: boolean;
}

export interface OwnershipChainEvent {
  kind: "registered" | "transfer";
  id?: string;
  status: string;
  owner_id?: string;
  owner_name?: string | null;
  from_id?: string;
  from_name?: string | null;
  to_id?: string | null;
  to_name?: string | null;
  to_email?: string;
  reason?: string | null;
  at?: string | null;
  created_at?: string | null;
  recipient_responded_at?: string | null;
  owner_confirmed_at?: string | null;
  completed_at?: string | null;
  ledger_tx_id?: string | null;
  is_current?: boolean;
  detail?: string;
}

export interface OwnershipChain {
  registration_id: string;
  current_owner_id: string;
  current_owner_name?: string | null;
  events: OwnershipChainEvent[];
  append_only: boolean;
  note: string;
  ownership: OwnershipState;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DashboardSummary {
  stats: {
    total_creations: number;
    owned_creations?: number;
    incoming_ownership?: number;
    verified_records: number;
    protected_ideas: number;
    team_projects: number;
    pending_transfers: number;
    active_disputes: number;
    security_alerts: number;
    unread_notifications: number;
    verified_proofs: number;
    active_shares: number;
  };
  charts: {
    registrations_by_month: { label: string; registrations: number }[];
    asset_types: { name: string; value: number }[];
    verification_split: { name: string; value: number }[];
    activity_heatmap: {
      date: string;
      registrations: number;
      ideas: number;
      proofs: number;
      versions: number;
      total: number;
    }[];
  };
}

export interface DashboardActivity {
  recent_registrations: Registration[];
  ledger_transactions: LedgerTransaction[];
  audit_timeline: AuditEntry[];
  verification_activity: {
    id: string;
    verification_id: string;
    registration: string | null;
    status: string;
    result: string | null;
    uses: number;
    max_uses: number;
    created_at: string;
    verified_at: string | null;
  }[];
  alerts: AlertItem[];
  team_activity: NotificationItem[];
  quick_actions: { label: string; path: string; icon: string }[];
}

export interface LedgerStatus {
  mode: string;
  label: string;
  connected: boolean;
  network: string;
  chain_id?: number | null;
  contract_address?: string | null;
  block_number?: number | null;
  last_hash?: string | null;
  tamper_detected?: boolean | null;
  errors?: string[];
  message?: string;
  latest_transaction?: LedgerTransaction | null;
  database_records?: number;
}

export interface LedgerTransaction {
  id: string;
  tx_id: string;
  block_number: number;
  tx_type: string;
  actor_id?: string | null;
  entity_type: string;
  entity_id: string;
  payload_digest: string;
  prev_hash: string;
  record_hash: string;
  mode: string;
  network: string;
  status: string;
  chain_tx_hash?: string | null;
  timestamp: string;
}

export interface AuditEntry {
  id: string;
  event_id: string;
  actor_id?: string | null;
  actor_ref: string;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  metadata?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
  record_hash: string;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  entity_type?: string | null;
  entity_id?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface Idea {
  id: string;
  idea_ref: string;
  title: string;
  description?: string | null;
  commitment: string;
  privacy: string;
  status: string;
  ledger_tx_id?: string | null;
  ledger_mode: string;
  created_at: string;
  revealed_at?: string | null;
  owner_id: string;
  is_demo: boolean;
  can_reveal: boolean;
  revisions?: {
    id: string;
    revision_no: number;
    notes: string;
    commitment: string;
    ledger_tx_id?: string | null;
    created_at: string;
  }[];
}

export interface VersionItem {
  id: string;
  registration_id: string;
  version_no: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  sha256: string;
  change_description?: string | null;
  contributor_id: string;
  contributor_name?: string | null;
  parent_version_id?: string | null;
  ledger_tx_id?: string | null;
  created_at: string;
}

export interface ProvenanceRecord {
  id: string;
  registration_id: string;
  declared_ai: boolean;
  model_name?: string | null;
  tool_name?: string | null;
  prompt_commitment?: string | null;
  human_contribution?: string | null;
  editing_details?: string | null;
  creation_date?: string | null;
  analysis_available: boolean;
  analysis?: Record<string, any> | null;
  ledger_tx_id?: string | null;
  created_at: string;
  registration_label?: string;
}

export interface TeamMemberItem {
  id: string;
  project_id: string;
  user_id?: string | null;
  email: string;
  display_name?: string | null;
  role: string;
  status: string;
  contribution_description?: string | null;
  ownership_percent: number;
  joined_at?: string | null;
  created_at: string;
}

export interface AllocationItem {
  id: string;
  project_id: string;
  member_id: string;
  member_email?: string | null;
  member_name?: string | null;
  percent: number;
  status: string;
  proposed_by: string;
  approvals: string[];
  created_at: string;
  approved_at?: string | null;
}

export interface Team {
  id: string;
  name: string;
  description?: string | null;
  owner_id: string;
  owner_name?: string | null;
  organization_id?: string | null;
  status: string;
  ledger_tx_id?: string | null;
  created_at: string;
  member_count: number;
  members: TeamMemberItem[];
  my_role?: string | null;
  my_status?: string | null;
  is_demo: boolean;
  can_manage?: boolean;
  contributions?: {
    id: string;
    member_id: string;
    member_name: string;
    description: string;
    file_reference?: string | null;
    status: string;
    approved_at?: string | null;
    created_at: string;
  }[];
  allocations?: AllocationItem[];
  allocation_total?: number;
  timeline?: { type: string; label: string; timestamp: string }[];
  creations?: TeamCreation[];
}

export interface TeamCreation {
  id: string;
  registration_id: string;
  title: string;
  asset_type: string;
  privacy: string;
  status: string;
  sha256: string;
  registered_at: string;
  owner_id: string;
  owner_name?: string | null;
}

export interface TeamContext {
  id: string;
  name: string;
  status: string;
  ledger_tx_id?: string | null;
  allocation_status: "approved" | "proposed" | null;
  allocation_total: number;
  members: {
    id: string;
    name: string;
    email: string;
    role: string;
    percent: number;
    ownership_percent: number;
  }[];
}

export interface AlertItem {
  id: string;
  registration_id: string;
  matched_registration_id: string;
  registration_label?: string | null;
  matched_label?: string | null;
  alert_type: string;
  similarity_score?: number | null;
  status: string;
  investigation_notes?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  matched_registration?: {
    registration_id?: string | null;
    title?: string | null;
    fingerprint?: string | null;
    registered_at?: string | null;
    status?: string | null;
    ledger_tx_id?: string | null;
    is_owner: boolean;
  };
  similarity_analyses?: { method: string; score: number; details?: Record<string, unknown>; created_at: string }[];
  disclaimer?: string;
}

export interface TransferItem {
  id: string;
  registration_id: string;
  registration_label?: string | null;
  registration_title?: string | null;
  from_user_id: string;
  from_name?: string | null;
  to_user_id?: string | null;
  to_name?: string | null;
  to_email: string;
  status: string;
  reason?: string | null;
  rejection_reason?: string | null;
  ledger_tx_id?: string | null;
  created_at: string;
  recipient_responded_at?: string | null;
  owner_confirmed_at?: string | null;
  completed_at?: string | null;
}

export interface DisputeItem {
  id: string;
  dispute_ref: string;
  registration_id: string;
  registration_label?: string | null;
  registration_title?: string | null;
  claimant_id: string;
  claimant_name?: string | null;
  respondent_id?: string | null;
  reason: string;
  description: string;
  status: string;
  resolution?: string | null;
  earliest_registration_id?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  registration?: {
    registration_id: string;
    title: string;
    sha256: string;
    registered_at: string;
    ledger_tx_id?: string | null;
    ledger_mode: string;
    owner_id: string;
  };
  respondent_name?: string | null;
  evidence?: {
    id: string;
    file_name: string;
    sha256: string;
    size_bytes: number;
    description?: string | null;
    uploaded_by: string;
    created_at: string;
  }[];
  can_review?: boolean;
  can_upload_evidence?: boolean;
}

export interface ShareItem {
  id: string;
  verification_id: string;
  verification_url: string;
  registration_id: string;
  registration_label: string;
  registration_title: string;
  status: string;
  result?: string | null;
  uses: number;
  max_uses: number;
  disclosure: Record<string, boolean>;
  message?: string | null;
  created_at: string;
  expires_at: string;
  verified_at?: string | null;
  expired: boolean;
}

export interface ProofResult {
  proof_id: string;
  proof: Record<string, any>;
  public_signals: Record<string, any>;
  scheme: string;
  statement: string;
  expires_at: string;
  verification_url?: string | null;
}

export interface TrustFactor {
  key: string;
  label: string;
  points: number;
  max: number;
  detail: string;
}

export interface TrustReport {
  score: number;
  grade: string;
  summary: string;
  factors: TrustFactor[];
  checked_at: string;
}

export interface IntegrityRecord {
  registration_id: string;
  title: string;
  asset_type: string;
  sha256: string;
  ledger_tx_id: string | null;
  ledger_ok: boolean;
  file_present: boolean;
  registered_at: string;
}

export interface IntegrityOverview {
  ledger: {
    valid: boolean;
    records: number;
    last_hash: string | null;
    errors: string[];
    mode: string;
    label: string;
    network: string;
    tamper_detected: boolean | null;
  };
  audit_chain: {
    valid: boolean;
    events: number;
    errors: string[];
    last_hash: string;
  };
  counts: Record<string, number>;
  checks: {
    missing_ledger_records: string[];
    missing_files: string[];
    duplicate_fingerprints: { sha256: string; count: number }[];
  };
  exposure: {
    open_alerts: number;
    public_fingerprint_records: number;
    audit_events: number;
  };
  workspace_digest: string;
  records: IntegrityRecord[];
  checked_at: string;
}
