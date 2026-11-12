from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph

from .render import (
    bullets,
    callout,
    chapter,
    checklist,
    code_block,
    gap,
    h2,
    h3,
    kv,
    lead,
    numbers,
    p,
    part_opener,
    table,
)
from .theme import GREY, INK, STYLES, TURRET


def part_five() -> list:
    return [
        *part_opener(
            "V",
            "TRUST AND OPERATIONS",
            "The security boundary, the complete API surface, the commands that run the product, the limitations that must be stated out loud, and a checklist anyone can use to reproduce the important claims.",
            [
                (37, "Security model and trust boundaries"),
                (38, "API map, status codes, and limits"),
                (39, "Running AUTHENTIQ"),
                (40, "Honest limitations"),
                (41, "Verification checklist and glossary"),
            ],
            note="This part is written for the person who has to defend the product to a client, an auditor, or another engineer. It names what is protected, what is not, and how to check.",
        ),
        *chapter(
            37,
            "Security model and trust boundaries",
            "Trust",
            "Security in AUTHENTIQ is not a single feature. It is the combination of password hashing, token rotation, backend authorization, encrypted storage, integrity checks, and an append-only audit trail.",
        ),
        h2("Implemented controls"),
        *table(
            ["Control", "Implementation", "What it protects"],
            [
                ["Password hashing", "Argon2id with per-password salts.", "Stolen database does not reveal passwords."],
                ["Access tokens", "JWT, 45 minutes, signed with the application secret.", "Short-lived API authorization."],
                ["Refresh tokens", "14 days, stored hashed, rotated on use.", "Longer sessions without long-lived bearer tokens."],
                ["Session revocation", "Session rows can be revoked individually or all at once.", "Lost devices and suspected compromise."],
                ["Login lockout", "Temporary lock after repeated failures.", "Online password guessing."],
                ["Rate limiting", "Sliding window per scope.", "Brute force, proof spam, share enumeration."],
                ["Backend authorization", "Ownership, organization, and role checks on every protected resource.", "Horizontal and vertical privilege escalation."],
                ["Encrypted files", "AES-256-GCM in AQVL1 containers.", "Files at rest on disk."],
                ["Encrypted secrets", "Fernet for idea text and commitment secrets.", "Sensitive database fields."],
                ["Integrity checks", "Chunk hashes, overall SHA-256, scanner gate.", "Corruption and tampering in transit."],
                ["Audit chain", "Hash-chained audit entries and a verification endpoint.", "Silent changes to security history."],
                ["Security headers and CORS", "Configured in the API and proxy.", "Common browser attack surface."],
            ],
            widths=[118, 220, 157],
            bold_first=True,
        ),
        gap(2),
        h2("Threats and residual risk"),
        *table(
            ["Threat", "Control", "Residual risk"],
            [
                ["Credential stuffing", "Argon2id, lockout, login rate limit.", "Distributed attempts across many IPs can still succeed slowly."],
                ["Token theft via XSS", "Short access lifetime, no third-party scripts, React escaping.", "localStorage is readable by injected script; a strict CSP is still required."],
                ["Horizontal access", "Resource-level ownership and organization checks.", "A logic bug in a new endpoint could bypass the helper."],
                ["Replay of a proof", "One-time nonce, expiry, registration binding, usage limits.", "A leaked valid package can be used within its limits if the link is shared."],
                ["Insider file access", "Encryption at rest, access checks.", "An operator with the secret key and filesystem can decrypt."],
                ["Ledger rewrite", "Hash chain and fsync.", "Filesystem access allows a full rebuild; not distributed consensus."],
                ["Database rollback", "Audit entries and chain verification.", "A consistent rollback of both data and audit entries may not be detectable."],
                ["Upload abuse", "Extension allow-list, size cap, scanner gate, rate limits.", "A zero-day in a parser or scanner remains possible."],
                ["Enumeration", "404 for hidden resources, scoped queries, rate limits.", "Timing and error differences are always a residual channel."],
            ],
            widths=[112, 190, 193],
            bold_first=True,
        ),
        gap(2),
        h2("What no role can do"),
        *bullets(
            [
                "Read another user's private registration without a share link or a reviewer role that covers it.",
                "Resolve a dispute that they are a party to as if they were neutral, unless they hold the verifier role or an organization admin scope over the record.",
                "Recover a commitment secret or a file password from the API; secrets are encrypted and never returned.",
                "Turn a local simulated ledger record into a public blockchain transaction without configuring the Polygon adapter.",
                "Bypass rate limits or account lockout by changing a route in the browser.",
            ]
        ),
        h2("The trust boundaries"),
        *kv(
            [
                ("Browser", "Untrusted. It may be modified, extended, or controlled by an attacker. Every value it sends is validated."),
                ("API", "Trusted application boundary. It holds the secret key, database credentials, and encryption key derivation."),
                ("Database", "Trusted infrastructure. Operator access is equivalent to full data access."),
                ("Filesystem", "Trusted infrastructure. Holds encrypted files, evidence, and the simulation ledger."),
                ("Polygon Amoy", "External, optional. A testnet is independent but not mainnet settlement."),
                ("Email and MFA providers", "Absent. The product reports them as unavailable instead of simulating them."),
            ]
        ),
        gap(8),
        h2("What the product does not claim"),
        *bullets(
            [
                "That a hash proves authorship or originality.",
                "That a local ledger is a blockchain or distributed consensus.",
                "That a proof establishes legal ownership.",
                "That the platform is a court, arbitrator, or custody service.",
                "That unavailable email, MFA, or AI classification is active.",
            ]
        ),
        callout(
            "The defensible claim",
            "AUTHENTIQ records exact bytes, binds them to a commitment, proves knowledge of the opening, and preserves a hash-chained history with explicit labels. Every part of that sentence is implemented and testable.",
            tone="lime",
        ),
    ]


def chapter_api() -> list:
    return [
        *chapter(
            38,
            "API map, status codes, and limits",
            "Trust",
            "Everything the browser does goes through /api. The OpenAPI document at /api/docs is the live contract; this chapter is the human map.",
        ),
        h2("Conventions"),
        *kv(
            [
                ("Base path", "/api. The frontend uses VITE_API_URL and defaults to /api."),
                ("Authentication", "Authorization: Bearer access_token. Refresh uses the refresh token in the JSON body."),
                ("Content types", "application/json for most requests; multipart/form-data for chunks and evidence."),
                ("Errors", "A JSON detail field. Status codes follow the table below."),
                ("Pagination", "Limit and offset query parameters where a list can grow."),
                ("Downloads", "Authenticated fetch, returned as a blob; no public file URLs."),
            ]
        ),
        gap(8),
        h2("System and authentication"),
        *table(
            ["Method", "Path", "Purpose"],
            [
                ["GET", "/health", "Status, version, ledger mode, proof scheme."],
                ["GET", "/docs, /redoc, /openapi.json", "Interactive and machine-readable API documentation."],
                ["POST", "/auth/register", "Create an individual or organization account."],
                ["POST", "/auth/login", "Sign in and create a session."],
                ["POST", "/auth/refresh", "Rotate the refresh token and issue a new access token."],
                ["POST", "/auth/logout", "Revoke one session or all sessions."],
                ["GET, PATCH", "/auth/me", "Read or update the current profile."],
                ["POST", "/auth/forgot-password", "Create a reset token."],
                ["POST", "/auth/reset-password", "Consume a reset token and set a new password."],
                ["POST", "/auth/change-password", "Change the password and revoke all sessions."],
                ["GET", "/auth/sessions", "List active sessions."],
                ["DELETE", "/auth/sessions/{session_id}", "Revoke one session."],
            ],
            widths=[86, 205, 204],
            bold_first=False,
        ),
        gap(2),
        h2("Uploads, fingerprints, and registrations"),
        *table(
            ["Method", "Path", "Purpose"],
            [
                ["POST", "/uploads/initiate", "Start a chunked upload and create a chunk plan."],
                ["POST", "/uploads/{upload_id}/chunk", "Upload and verify one chunk."],
                ["POST", "/uploads/{upload_id}/complete", "Assemble, scan, hash, and encrypt."],
                ["GET", "/uploads/{upload_id}", "Upload status."],
                ["POST", "/fingerprints/generate", "Compute SHA-256 over a supplied file."],
                ["POST", "/fingerprints/verify", "Compare a hash with a fingerprint."],
                ["POST", "/registrations", "Create a registration from a completed upload."],
                ["POST", "/registrations/duplicate-check", "Check a fingerprint before upload."],
                ["GET", "/registrations", "List accessible registrations."],
                ["GET", "/registrations/{identifier}", "Registration detail."],
                ["GET", "/registrations/{identifier}/file", "Decrypt and download the original."],
                ["GET", "/registrations/{identifier}/certificate", "Download the PDF certificate."],
                ["GET", "/registrations/{identifier}/trust-score", "Explainable evidence score."],
                ["GET", "/registrations/{identifier}/evidence-packet", "Download the ZIP packet."],
                ["GET", "/registrations/{identifier}/verification-state", "Ledger record and recent proofs."],
            ],
            widths=[86, 250, 159],
            bold_first=False,
        ),
        gap(2),
        h2("Proofs, sharing, ideas, and versions"),
        *table(
            ["Method", "Path", "Purpose"],
            [
                ["POST", "/zkp/challenge", "Create a one-time nonce."],
                ["POST", "/zkp/generate", "Generate a proof from a local fingerprint."],
                ["POST", "/zkp/verify", "Verify a proof."],
                ["GET", "/zkp/proofs/{registration_id}", "List recent proofs."],
                ["POST", "/sharing/create", "Create a verification link and package."],
                ["GET", "/sharing", "List links created by the user."],
                ["DELETE", "/sharing/{verification_id}", "Revoke a link."],
                ["GET, POST", "/public/verify/{verification_id}", "Read disclosure-limited metadata or submit a proof."],
                ["POST, GET", "/ideas", "Create or list ideas."],
                ["GET", "/ideas/{identifier}", "Idea detail."],
                ["POST", "/ideas/{identifier}/revisions", "Add an encrypted revision."],
                ["PATCH", "/ideas/{identifier}/notes", "Update encrypted notes."],
                ["POST", "/ideas/{identifier}/reveal", "Reveal and record the event."],
                ["GET", "/ideas/{identifier}/certificate", "Idea certificate."],
                ["GET", "/ideas/{identifier}/evidence", "Idea evidence package."],
                ["POST", "/versions", "Add a version from a completed upload."],
                ["GET", "/versions/registration/{registration_id}", "List versions."],
                ["GET", "/versions/compare", "Compare two versions."],
                ["GET", "/versions/{version_id}", "Version detail."],
                ["GET", "/versions/{version_id}/file", "Download a version."],
                ["GET", "/versions/{version_id}/certificate", "Version certificate."],
            ],
            widths=[86, 250, 159],
            bold_first=False,
        ),
        gap(2),
        h2("Collaboration, governance, and trust"),
        *table(
            ["Method", "Path", "Purpose"],
            [
                ["POST, GET", "/teams", "Create or list team projects."],
                ["GET", "/teams/{project_id}", "Project detail."],
                ["POST", "/teams/{project_id}/invite", "Invite a member and issue an invite code."],
                ["POST", "/teams/{project_id}/join", "Accept an invitation."],
                ["POST", "/teams/redeem", "Redeem an invite code and join the issuing project."],
                ["POST", "/teams/{project_id}/contributions", "Submit a contribution."],
                ["PATCH", "/teams/{project_id}/contributions/{id}/approve", "Approve a contribution."],
                ["POST", "/teams/{project_id}/ownership/propose", "Propose percentages."],
                ["POST", "/teams/{project_id}/ownership/approve", "Approve an allocation."],
                ["GET", "/teams/{project_id}/ownership", "Allocation state."],
                ["GET", "/teams/{project_id}/certificate", "Team certificate."],
                ["POST, GET", "/transfers", "Propose or list transfers."],
                ["GET", "/transfers/history/{registration_id}", "Append-only transfer history."],
                ["POST", "/transfers/{id}/accept, reject, cancel, confirm", "Transfer transitions."],
                ["POST, GET", "/disputes", "Open or list disputes."],
                ["GET", "/disputes/{dispute_id}", "Dispute detail."],
                ["POST", "/disputes/{dispute_id}/evidence", "Upload encrypted evidence."],
                ["GET", "/disputes/{dispute_id}/evidence/{evidence_id}", "Download evidence."],
                ["POST", "/disputes/{dispute_id}/status", "Update or resolve a dispute."],
                ["GET", "/disputes/{dispute_id}/report", "JSON evidence report."],
                ["GET", "/alerts, /alerts/{id}", "List or inspect alerts."],
                ["PATCH", "/alerts/{id}/status", "Update the investigation state."],
                ["GET", "/ledger/status, /ledger/transactions", "Ledger status and transactions."],
                ["GET", "/ledger/transactions/{tx_id}", "Transaction detail."],
                ["POST", "/ledger/audit", "Verify the active ledger."],
                ["GET", "/integrity/overview", "Full integrity report."],
                ["GET", "/notifications", "Inbox."],
                ["PATCH", "/notifications/{id}/read", "Mark one read."],
                ["POST", "/notifications/read-all", "Mark all read."],
                ["DELETE", "/notifications/{id}", "Dismiss."],
                ["GET", "/audit-logs, /audit-logs/verify", "Audit list and chain verification."],
                ["GET", "/search?q=", "Cross-entity search."],
                ["GET, PATCH", "/settings/organization", "Organization details, members, invitations, and rename."],
                ["POST", "/settings/organization/members", "Provision a member account with a generated password."],
                ["POST", "/settings/organization/members/{id}/password", "Rotate a member password and revoke sessions."],
                ["GET, POST", "/settings/organization/invitations", "List and issue organization invitation codes."],
                ["POST", "/settings/organization/invitations/accept", "Redeem an organization invitation code."],
                ["DELETE", "/settings/organization/invitations/{id}", "Revoke an unaccepted invitation."],
                ["GET", "/settings/organization/registrations", "Organization registrations."],
                ["GET", "/settings/security", "Security capability report."],
                ["GET", "/dashboard/summary, /dashboard/activity", "Dashboard data."],
                ["GET", "/public/records", "Public records registry."],
                ["GET", "/admin/overview, /admin/users, /admin/organizations", "Site administration overview and lists."],
                ["GET, PATCH", "/admin/users/{id}, /admin/disputes/{id}", "Site administration writes."],
            ],
            widths=[86, 250, 159],
            bold_first=False,
        ),
        gap(2),
        h2("Status codes"),
        *table(
            ["Status", "Meaning"],
            [
                ["400", "Invalid state or bad request."],
                ["401", "Missing, expired, or invalid token."],
                ["403", "Authenticated but not authorized."],
                ["404", "Not found, or hidden by access control."],
                ["409", "State conflict, duplicate, replay, or usage limit."],
                ["410", "Expired or revoked resource."],
                ["413 / 415", "File too large or unsupported extension."],
                ["422", "Validation failure or integrity mismatch."],
                ["423", "Account temporarily locked."],
                ["429", "Rate limit exceeded; inspect Retry-After."],
                ["500", "Unexpected server error."],
            ],
            widths=[90, 405],
            bold_first=True,
        ),
        gap(2),
        h2("Rate limits"),
        *table(
            ["Scope", "Limit", "Window"],
            [
                ["Login", "8 per IP and email", "5 minutes"],
                ["Registration", "10 per IP", "1 hour"],
                ["Proof generation", "40 per user", "1 hour"],
                ["Share creation", "30 per user", "1 hour"],
                ["Public verification", "30 per IP", "10 minutes"],
            ],
            widths=[180, 160, 155],
            bold_first=True,
        ),
        gap(2),
        callout(
            "The live contract wins",
            "This table is a map, not the schema. Before integrating, read /api/openapi.json and the docs/API.md reference for exact payload fields and validation rules.",
        ),
    ]


def chapter_running() -> list:
    return [
        *chapter(
            39,
            "Running AUTHENTIQ",
            "Operations",
            "The product runs locally with Python and Node. The current workspace uses a hosted Neon database; SQLite remains the zero-setup fallback. Docker Compose provides a production-like topology.",
        ),
        h2("Prerequisites"),
        *bullets(
            [
                "Python 3.11 or newer. The container uses 3.12; local verification used 3.14.",
                "Node.js 20 or newer and npm.",
                "Optional: Docker Desktop for the Compose topology.",
                "Optional: a PostgreSQL URL such as Neon for shared state.",
            ]
        ),
        h2("Backend"),
        code_block(
            [
                "cd backend",
                "python -m venv .venv",
                ".venv\\Scripts\\python.exe -m pip install -r requirements.txt",
                ".venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000",
            ]
        ),
        p(
            "The API runs at http://localhost:8000. Health is at /api/health, Swagger at /api/docs, ReDoc at /api/redoc. On startup the application creates directories and tables, and optionally seeds demo accounts when AUTHENTIQ_SEED_DEMO is true."
        ),
        h2("Frontend"),
        code_block(
            [
                "cd frontend",
                "npm install",
                "npm run dev",
            ]
        ),
        p(
            "Vite runs at http://localhost:5173 and proxies /api to http://localhost:8000. The landing page is /, the workspace sign-in is /login. A production build runs tsc --noEmit followed by vite build; the static output can be served by Nginx with history fallback."
        ),
        h2("Database"),
        p(
            "Set AUTHENTIQ_DATABASE_URL in backend/.env to use PostgreSQL. The active workspace points at a Neon pooled connection with sslmode=require and channel_binding=require. Without the variable, the backend uses backend/authentiq.db. Tables are created at startup; there is no migration history yet."
        ),
        h2("Demo accounts"),
        *table(
            ["Role", "Email", "Password"],
            [
                ["Organization admin", "demo@authentiq.dev", "Authentiq!Demo2026"],
                ["Verifier", "verifier@authentiq.dev", "Authentiq!Verify2026"],
                ["Creator", "maya@authentiq.dev", "Authentiq!Team2026"],
            ],
            widths=[145, 195, 155],
            bold_first=True,
        ),
        p(
            "The seed creates only these three logins. It creates no registrations, ideas, teams, alerts, transfers, disputes, shares, ledger events, or audit entries. The workspaces start empty by design, so the first dashboard is a true zero state."
        ),
        h2("Verification commands"),
        code_block(
            [
                "cd backend",
                ".venv\\Scripts\\python.exe -m pytest -q",
                "",
                "cd frontend",
                "npm run build",
            ]
        ),
        p("The backend suite currently passes 76 tests. The frontend build passes TypeScript checking and Vite bundling; the only expected warning is Vite's chunk-size advisory."),
        h2("Docker Compose"),
        code_block(
            [
                "copy .env.example .env",
                "docker compose up --build",
                "docker compose exec backend python -m app.seed",
            ]
        ),
        p(
            "The Compose topology runs PostgreSQL 16, the backend, and an Nginx-served frontend. Nginx listens on 8080, proxies /api to the backend on 8000, and serves the SPA with history fallback. PostgreSQL and the storage directory use named volumes. The backend waits for the database health check before starting."
        ),
        h2("Health check"),
        code_block(
            [
                "GET http://localhost:8000/api/health",
                "{ status, version, ledger_mode, zkp_scheme, database }",
            ]
        ),
        gap(2),
        h2("Troubleshooting"),
        *table(
            ["Symptom", "Likely cause", "Fix"],
            [
                ["401 on every request", "Expired access token or missing refresh token.", "Sign in again; check that localStorage holds both tokens."],
                ["CORS error in the browser", "Origin not in AUTHENTIQ_CORS_ORIGINS.", "Add the exact scheme, host, and port."],
                ["Database connection timeout", "Neon paused, wrong URL, or network block.", "Wake the database, verify the URL, check port 5432 access."],
                ["Upload completes but registration fails", "Upload not owned by the user or not completed.", "Re-initiate and complete the upload before registering."],
                ["Proof generation disabled", "Local hash does not match the registered fingerprint.", "Select the exact original file; even one changed byte changes the hash."],
                ["Share link returns 410", "Expired or revoked.", "Create a new link with a longer expiry."],
                ["Ledger chip says simulation", "Default mode.", "That is expected unless the Polygon adapter is configured."],
            ],
            widths=[142, 190, 163],
            bold_first=True,
        ),
    ]


def chapter_limits() -> list:
    return [
        *chapter(
            40,
            "Honest limitations",
            "Trust",
            "These are the boundaries a serious operator must be able to say out loud. None of them is hidden in the interface, and none should be omitted from a sales conversation.",
        ),
        h2("The ten limits that matter"),
        *table(
            ["Limitation", "What it means", "What to do about it"],
            [
                ["Local ledger is simulated", "It detects local tampering but is not distributed consensus and can be rewritten by an operator.", "Use the Polygon adapter when independent timestamp evidence is required."],
                ["Proof scope is narrow", "The default proof proves knowledge of the commitment opening; file equality is checked outside the circuit.", "State the claim precisely; do not call it authorship proof."],
                ["No legal determination", "Registration is priority evidence, not a court judgment or copyright registration.", "Keep the certificate and packet as supporting evidence; consult counsel."],
                ["No email delivery", "Password reset returns a development token, and team invitations are delivered as a one-time invite code shown to the owner.", "Configure a provider before production and send the code by mail."],
                ["No MFA or passkeys", "Account security depends on password, token hygiene, and device security.", "Add TOTP or WebAuthn before handling high-value accounts."],
                ["Files are local", "Encrypted files and the ledger are on disk, not object storage.", "Use encrypted volumes, off-box backups, and a restore test."],
                ["No migration history", "Tables are created from metadata at startup; schema changes are not versioned.", "Generate an Alembic baseline and run migrations separately."],
                ["In-process rate limiting", "Multiple workers do not share counters.", "Move limits to Redis or the edge before scaling horizontally."],
                ["No background workers", "Hashing, encryption, and certificate generation are synchronous request work.", "Add a queue for large files and report generation."],
                ["AI analysis is unavailable", "No provider credentials are configured; the UI reports that honestly.", "Configure a real provider or leave the analysis action hidden."],
            ],
            widths=[128, 195, 172],
            bold_first=True,
        ),
        gap(2),
        h2("Claims to avoid"),
        *bullets(
            [
                "Do not say the product is a blockchain by default. Say it uses an append-only local ledger with hash chaining, with an optional Polygon testnet adapter.",
                "Do not say a proof proves authorship. Say it proves knowledge of the commitment opening and that the file hash is checked separately.",
                "Do not say registration creates a copyright. Say it creates dated priority evidence.",
                "Do not say the platform is court-admissible. Say it produces portable evidence that a reviewer can inspect.",
                "Do not say files are stored in the cloud. Say relational state is hosted and encrypted files and the ledger are on local disk in this deployment.",
            ]
        ),
        h2("What is already stronger than a prototype norm"),
        *checklist(
            [
                "Real SHA-256, Poseidon, BN254, Pedersen, and Schnorr code, not mocked responses.",
                "Real chunk verification, encryption, certificates, and evidence packets.",
                "Backend-enforced roles with tests for authorization failures.",
                "A test suite that deliberately tampers with proofs, ledgers, and audit chains.",
                "Honest availability flags for missing email, MFA, passkeys, and AI analysis.",
                "A deterministic, explainable trust score instead of a single unexplained badge.",
            ]
        ),
        gap(4),
        callout(
            "The standard to hold",
            "The product should be described at the strength of its weakest true sentence, not its strongest marketing sentence. That is how trust products survive contact with a skeptical reviewer.",
        ),
    ]


def chapter_checklist() -> list:
    story: list = [
        *chapter(
            41,
            "Verification checklist and glossary",
            "Appendix",
            "You do not have to take this handbook on faith. These are the checks you can run to confirm the important claims, followed by the vocabulary needed to discuss them precisely.",
        ),
        h2("Ten checks you can run"),
        *numbers(
            [
                "<b>Hash the same file twice.</b> The SHA-256 value must be identical, and changing one byte must change it completely.",
                "<b>Upload a file with a corrupted chunk.</b> The API must return 422 and refuse to complete the upload.",
                "<b>Register a file, then register the identical bytes again.</b> The second registration must succeed but create duplicate alerts and notifications.",
                "<b>Generate a proof with a different file.</b> The proof must be refused or fail verification because the fingerprint does not match.",
                "<b>Reuse a verification package after its use limit.</b> The API must return 409, not a success.",
                "<b>Open an expired or revoked share.</b> The API must return 410.",
                "<b>Edit one byte in ledger.jsonl and run the audit.</b> Verification must report a mismatch at the edited record.",
                "<b>Edit one audit entry and run the audit-chain check.</b> The chain must fail at the edited entry.",
                "<b>Sign in as a creator and request another user's registration.</b> The API must return 404 or 403, never the record.",
                "<b>Change a password and reuse an old refresh token.</b> The refresh must fail because every session was revoked.",
            ]
        ),
        gap(4),
        KeepTogether(
            table(
                ["Check", "Expected result", "Where to look"],
                [
                    ["Chunk integrity", "422 and no recorded chunk", "Upload endpoint response"],
                    ["Duplicate detection", "Registration plus alerts and notifications", "Alerts page and registration result"],
                    ["Proof mismatch", "Proof refused or invalid", "Verification page and proof list"],
                    ["Share reuse", "409", "Public verification endpoint"],
                    ["Expired share", "410", "Public verification endpoint"],
                    ["Ledger tamper", "First mismatch with block number", "Integrity center and ledger audit"],
                    ["Audit tamper", "First mismatch with entry id", "Audit chain verify"],
                    ["Cross-account access", "403 or 404", "Registration detail endpoint"],
                    ["Revoked session", "401 on refresh", "Auth refresh endpoint"],
                    ["Invite code reuse", "404 on the second redeem", "Teams redeem endpoint"],
                ],
                widths=[140, 200, 155],
                bold_first=True,
            )
        ),
        gap(2),
        h2("Glossary"),
        *table(
            ["Term", "Meaning in AUTHENTIQ"],
            [
                ["Access token", "A 45-minute JWT used as a bearer credential for API requests."],
                ["AQVL1", "The versioned encrypted container format for uploaded files and evidence."],
                ["Audit chain", "A hash-chained log of security-relevant actions, separate from the ledger."],
                ["Commitment", "A hiding commitment C = sG + rH that binds a fingerprint and secret without revealing them."],
                ["Creator", "The default role for every public registration; scope is the user's own resources."],
                ["dHash-64", "A 64-bit perceptual image hash used for near-duplicate detection."],
                ["Evidence packet", "A ZIP with manifest, certificate, ledger receipt, file digest, and verification instructions."],
                ["Fingerprint", "The SHA-256 digest of the exact file bytes."],
                ["Fiat-Shamir", "The transform that makes the Schnorr proof non-interactive by hashing the challenge."],
                ["Integrity center", "The diagnostic page that recomputes both chains, storage presence, linkage, and duplicates."],
                ["Ledger", "The append-only JSONL event history; simulated locally, optionally anchored on Polygon Amoy."],
                ["Manifest", "The canonical JSON description of an evidence packet, including its own SHA-256."],
                ["Org admin", "The organization owner role; adds organization records and in-organization dispute review."],
                ["Ownership DNA", "A deterministic grid derived from the fingerprint bits."],
                ["Pedersen commitment", "The BN254 commitment used by the Schnorr proof."],
                ["Poseidon-254", "The BN254-friendly hash used to derive the committed value."],
                ["Proof package", "A JSON package containing public signals and the proof, verifiable without the file."],
                ["Refresh token", "A 14-day token stored hashed and rotated on use."],
                ["Registration", "The dated record that binds a file fingerprint, commitments, metadata, and ledger event."],
                ["Schnorr proof", "The non-interactive proof of knowledge of the commitment opening."],
                ["Silent sharing", "A disclosure-limited verification link with an expiry and use limit."],
                ["Simulation ledger", "The default local append-only ledger, clearly labelled as simulated."],
                ["Trust score", "An explainable 0-100 evidence score with positive factors and penalties."],
                ["Verifier", "A reviewer role that can see all disputes and all ledger events, but not all registrations."],
                ["ZKP", "Zero-knowledge proof; in this product, the Schnorr proof over BN254 G1."],
            ],
            widths=[128, 367],
            bold_first=True,
        ),
        gap(4),
        h2("Closing"),
        p(
            "AUTHENTIQ is a working engineering prototype with real cryptography, real authorization, real storage encryption, and a real test suite. It is also a product with explicit boundaries: a local ledger, a narrow proof statement, no email, no MFA, and no legal authority. The value is not that it hides those boundaries. The value is that it gives a creator a precise, portable, privacy-preserving way to say: this is the work, this is when I recorded it, and this is how you can check."
        ),
        gap(6),
        callout(
            "Keep this with the product",
            "When the code changes, re-run the tests, update the version numbers, and re-check the claims in this handbook. A document that drifts from the implementation becomes the most expensive kind of fiction.",
            tone="lime",
        ),
        gap(14),
        Paragraph("AUTHENTIQ", ParagraphStyle("end-mark", fontName=TURRET, fontSize=20, leading=24, textColor=INK)),
        Paragraph("EVIDENCE, NOT ASSUMPTION.", ParagraphStyle("end-tag", fontName=STYLES["eyebrow"].fontName, fontSize=7, leading=10, textColor=GREY)),
    ]
    return story


def part_five_story() -> list:
    return [
        *part_five(),
        *chapter_api(),
        *chapter_running(),
        *chapter_limits(),
        *chapter_checklist(),
    ]
