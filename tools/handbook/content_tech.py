from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .render import (
    bullets,
    callout,
    chapter,
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


def part_four() -> list:
    return [
        *part_opener(
            "IV",
            "TECHNOLOGY A TO Z",
            "Every layer from the browser to the database, including the parts a user never sees: hashing, commitments, proofs, encryption, the ledger adapter, PDF generation, storage, and the documentation set.",
            [
                (28, "Architecture at a glance"),
                (29, "Frontend stack A to Z"),
                (30, "Frontend storage and browser state"),
                (31, "Backend stack A to Z"),
                (32, "Data layer and schema"),
                (33, "Cryptography"),
                (34, "Blockchain and ledger tooling"),
                (35, "Files, PDFs, and QR codes"),
                (36, "Infrastructure, documentation, and configuration"),
            ],
            note="Version numbers come from the manifests and documentation in this repository. Where the local environment and the container differ, both are named. Anything optional is labelled optional.",
        ),
        *chapter(
            28,
            "Architecture at a glance",
            "Technology",
            "AUTHENTIQ is a three-tier application with a cryptography-heavy backend. The browser renders and hashes; the API authorizes, proves, encrypts, and records; PostgreSQL and local storage persist.",
        ),
        h2("The tiers"),
        *table(
            ["Tier", "Technology", "Responsibility", "Trust posture"],
            [
                ["Browser", "React 18, TypeScript, Vite, TanStack Query", "Render the interface, hash files locally, upload chunks, hold the session in localStorage.", "Untrusted. Every claim is rechecked by the server."],
                ["API", "FastAPI, Pydantic, SQLAlchemy, Uvicorn", "Authenticate, authorize, validate, hash, prove, encrypt, certify, audit.", "Trusted application boundary."],
                ["Data", "PostgreSQL (Neon) for state; local disk for files, evidence, and the ledger", "Relational records, encrypted file containers, append-only history.", "Trusted infrastructure. Operator access is the residual risk."],
            ],
            widths=[58, 140, 180, 117],
            bold_first=True,
        ),
        gap(4),
        h2("A request from click to record"),
        *numbers(
            [
                "The browser sends a JSON or multipart request with a bearer access token when the route is protected.",
                "FastAPI validates the payload, resolves the database session, and loads the current user and session from the database.",
                "The route calls a service or performs the domain operation. Authorization is checked against the resource, not only the route.",
                "Domain code hashes, encrypts, proves, or writes an audit entry. Cryptography runs in-process; there is no external proving service.",
                "SQLAlchemy commits relational state. File writes happen in the storage layer. The ledger append calls fsync.",
                "A response is shaped by a serializer. Errors become the documented 4xx or 5xx codes; unhandled exceptions become a generic 500.",
            ]
        ),
        gap(2),
        h2("Repository map"),
        *table(
            ["Path", "What lives there"],
            [
                ["backend/app/api/", "HTTP routers by domain: auth, uploads, registrations, zkp, sharing, ideas, versions, provenance, teams, transfers, disputes, alerts, ledger, integrity, notifications, audit, search, settings, dashboard."],
                ["backend/app/services/", "Registration, access control, analysis, certificates, evidence and trust, notifications, serializers, integrity, audit."],
                ["backend/app/zkp/ and app/fingerprint/", "Poseidon, BN254, Schnorr, SHA-256, chunk hashing, canonical JSON."],
                ["backend/app/security/", "Argon2id, JWT, encryption, rate limiting, file scanning."],
                ["backend/app/storage/ and app/ledger/", "AQVL1 encrypted containers and the simulation or Polygon ledger adapters."],
                ["backend/app/models/ and app/schemas/", "29 SQLAlchemy tables and Pydantic request and response contracts."],
                ["frontend/src/pages/", "The landing page and every workspace screen."],
                ["frontend/src/components/", "Shell, brand, common states, UI primitives, and domain widgets."],
                ["frontend/src/lib/", "The single API client, upload client, formatting, and helpers."],
                ["frontend/src/styles/", "The house stylesheet and the application theme."],
                ["blockchain/ and circuits/", "Optional Solidity registry, Hardhat project, and Circom ownership circuit."],
                ["docs/ and storage/", "Six documents and the runtime file store."],
            ],
            widths=[195, 300],
            bold_first=True,
        ),
        gap(4),
        h2("Trust boundaries"),
        *kv(
            [
                ("Browser to API", "TLS in a real deployment. The API never trusts the browser's hash, role, ownership, or proof claims."),
                ("API to database", "A single trusted connection string from the environment. The database is not exposed to the browser."),
                ("API to filesystem", "Encrypted containers for completed files; temporary plaintext chunks exist briefly during upload."),
                ("API to ledger", "A local adapter with fsync, or a Polygon adapter that fails closed if configuration is missing."),
                ("Operator", "Can read the database and filesystem. Can rewrite the local ledger and audit chain. Proper deployment requires a secret manager, encrypted volumes, and off-box retention."),
            ]
        ),
        gap(8),
        h2("Deployment topologies"),
        *table(
            ["Mode", "Topology", "Use"],
            [
                ["Local development", "Vite :5173 to FastAPI :8000 to SQLite or Neon plus local storage and JSONL ledger.", "Fast iteration, deterministic tests, zero external dependencies."],
                ["Hosted state", "The current workspace: FastAPI to Neon PostgreSQL, with files and ledger on local disk.", "A shared relational database without moving encrypted files off the machine."],
                ["Docker Compose", "Nginx :8080 serves the SPA and proxies /api to FastAPI :8000, which uses PostgreSQL :5432 and a /data volume.", "A reproducible, production-like topology for evaluation."],
            ],
            widths=[95, 268, 132],
            bold_first=True,
        ),
        callout(
            "The important split",
            "Relational state lives in PostgreSQL. Encrypted files, evidence, and the simulation ledger live on local disk. Back up both, and do not assume that a database backup contains the files or the ledger.",
        ),
    ]


def chapter_frontend() -> list:
    return [
        *chapter(
            29,
            "Frontend stack A to Z",
            "Technology",
            "The frontend is a React single-page application built with Vite and TypeScript. It owns rendering, local hashing, chunked uploads, and session display; it never owns authorization.",
        ),
        *table(
            ["Package", "Version", "Where it is used", "Why it is there"],
            [
                ["React", "18.3", "Every component and page.", "Component model and UI runtime."],
                ["React DOM", "18.3", "Browser rendering.", "Mounts the SPA."],
                ["TypeScript", "5.7", "All source files.", "Static typing and build-time checking."],
                ["Vite", "6.0", "Development server and production build.", "Fast startup, static output, /api proxy."],
                ["@vitejs/plugin-react", "4.x", "vite.config.ts.", "React fast refresh and JSX transforms."],
                ["React Router", "6.28", "App.tsx and the shell.", "Public and protected route trees, redirects, location state."],
                ["TanStack Query", "5.62", "Every data screen.", "Server-state caching, mutations, invalidation, retries."],
                ["React Hook Form", "7.54", "Sign-up, registration, idea, team, dispute, and settings forms.", "Form state with minimal re-renders."],
                ["Zod", "3.24", "Form schemas and validation messages.", "Typed validation close to the form."],
                ["@hookform/resolvers", "3.9", "Form integration.", "Connects Zod schemas to Hook Form."],
                ["Tailwind CSS", "3.4", "All styling.", "Utility classes and semantic tokens."],
                ["Radix UI", "1.x and 2.x", "Dialog, dropdown, label, tabs, slot.", "Accessible primitives without a heavy component framework."],
                ["class-variance-authority", "0.7", "Button and UI variants.", "Typed variant definitions."],
                ["tailwind-merge", "2.6", "The cn() helper.", "Conflict-free class composition."],
                ["Lucide React", "0.468", "Icons across the shell and pages.", "Consistent stroke icon set."],
                ["Recharts", "2.15", "Dashboard charts and heatmap support.", "Composable SVG charts."],
                ["Framer Motion", "11.15", "Page and component transitions.", "Declarative motion with reduced-motion support."],
                ["Sonner", "1.7", "Toast feedback.", "Short, accessible success and error messages."],
                ["date-fns", "4.1", "Date formatting and relative time.", "Small, tree-shakeable date utilities."],
                ["Funnel Display", "woff2", "Body and interface copy.", "Self-hosted brand type, no external font request."],
                ["Turret Road", "woff2", "Display headings.", "Self-hosted geometric display type."],
            ],
            widths=[118, 48, 170, 159],
            bold_first=True,
        ),
        gap(2),
        h2("The design system in code"),
        *table(
            ["Token", "Value", "Where it appears"],
            [
                ["--paper", "#FFFFFF", "Page and card background."],
                ["--light", "#EAEAEA", "Secondary surfaces, table alternation, callouts."],
                ["--dark", "#171717", "Ink, primary text, borders, header bars."],
                ["--lime", "#B7FF00", "Accent, focus ring, highlights, chart emphasis."],
                ["--muted-foreground", "#888888", "Secondary text, labels, inactive states."],
                ["--border", "#D0D0D0", "Card edges and table rules."],
                ["--warning", "#454545", "Dark grey caution state."],
            ],
            widths=[128, 80, 287],
            bold_first=True,
        ),
        gap(4),
        p(
            "The landing stylesheet is loaded before the application stylesheet, so the palette, type faces, and base element rules apply to the workspace too. The Tailwind theme maps semantic tokens onto the same values and remaps the legacy blue, indigo, violet, emerald, and slate scales onto ink, lime, and neutral greys. There is one theme and no theme switch, which prevents surface drift."
        ),
        h2("Build and runtime conventions"),
        *bullets(
            [
                "<b>One HTTP entry point.</b> src/lib/api.ts adds the bearer token, performs a single-flight refresh on 401, retries once, extracts errors, and handles authenticated blob downloads.",
                "<b>One upload client.</b> src/lib/upload.ts slices the file, hashes each chunk, sends it, and tracks progress.",
                "<b>Session restoration.</b> AuthContext validates the stored token with /api/auth/me; the cached profile is a display shortcut.",
                "<b>Protected routing.</b> ProtectedShell redirects unauthenticated users to /login and stores the attempted path in location state.",
                "<b>Build.</b> npm run build runs tsc --noEmit and then vite build. The output is a static bundle that Nginx can serve with history fallback.",
            ]
        ),
        callout(
            "What the browser does not decide",
            "The client can hide a button, but it cannot grant a role, approve a proof, or read a registration the API refuses to return. Route visibility is user experience; backend authorization is the boundary.",
        ),
    ]


def chapter_browser_storage() -> list:
    return [
        *chapter(
            30,
            "Frontend storage and browser state",
            "Technology",
            "The browser stores exactly three values for authentication, keeps server data in memory, and uses short-lived blob URLs for protected downloads. There is no IndexedDB, service worker cache, or cookie-based session.",
        ),
        h2("What is stored where"),
        *table(
            ["Mechanism", "Key or use", "Lifetime", "Why"],
            [
                ["localStorage", "authentiq_access_token", "Until logout or expiry", "Bearer token for API requests."],
                ["localStorage", "authentiq_refresh_token", "14 days or until revoked", "Rotates the access token after a 401."],
                ["localStorage", "authentiq_user", "Until logout", "Cached profile for fast rendering; not an authorization source."],
                ["TanStack Query cache", "Server responses by query key", "In memory until reload or invalidation", "Avoids duplicate fetches and keeps screens fast."],
                ["Blob URLs", "Authenticated file and certificate downloads", "Until revoked after the click", "Lets the browser download a protected response without a public URL."],
                ["File API", "The selected file", "Until the upload finishes", "Chunk slicing and local SHA-256."],
                ["Web Crypto", "SHA-256 digest", "Request-scoped", "Client-side fingerprint feedback and duplicate check."],
            ],
            widths=[105, 160, 105, 125],
            bold_first=True,
        ),
        gap(4),
        h2("What is deliberately not stored"),
        *bullets(
            [
                "No session cookie. Authentication uses explicit bearer headers.",
                "No IndexedDB or offline database. The workspace requires the API.",
                "No service worker cache. A stale bundle cannot quietly serve old authorization logic.",
                "No commitment secret, file key, or raw password. Those never reach the browser.",
                "No analytics identifier or third-party script. Fonts are self-hosted.",
            ]
        ),
        h2("The refresh flow"),
        p(
            "When a protected request returns 401, the API client starts one refresh request and shares it across concurrent failures. On success it replaces both tokens and the cached user, then retries the original request once. On failure it clears all three localStorage keys and sends the user to /login. That single-flight behavior prevents a burst of parallel refreshes from invalidating its own rotation chain."
        ),
        h2("Download handling"),
        p(
            "Protected files, certificates, and evidence packets are fetched with the bearer token, converted to a Blob, and exposed through a temporary object URL. The URL is revoked after the download is triggered. A user cannot copy a durable public file URL out of the interface because one does not exist."
        ),
        h2("Upload handling"),
        p(
            "The file is read in slices of at most 8 MB. Each slice is hashed with Web Crypto and sent as multipart form data. The browser keeps only the current slice and the accumulated progress in memory. The overall digest is declared at completion and recomputed by the server. This keeps memory bounded even for a 200 MB file."
        ),
        callout(
            "The trade-off to understand",
            "Storing tokens in localStorage is simple and works with a static SPA, but it means an XSS bug could read them. The mitigation is a strict content policy, no third-party scripts, React escaping, and short access-token lifetimes. A production system with a same-site backend should consider an HttpOnly cookie with CSRF protection.",
        ),
        h2("Clearing state"),
        *kv(
            [
                ("Logout", "Calls /api/auth/logout, revokes the refresh token, removes all three keys, clears the query cache, and navigates to /login."),
                ("Refresh failure", "Removes local credentials and returns to sign-in with the attempted path."),
                ("Password change", "The server revokes every session; the current client is signed out on the next refresh."),
                ("Session revocation", "A revoked session cannot refresh even if the browser still holds the old token."),
            ]
        ),
    ]


def chapter_backend() -> list:
    return [
        *chapter(
            31,
            "Backend stack A to Z",
            "Technology",
            "The backend is a synchronous FastAPI application. It validates, authorizes, hashes, proves, encrypts, certifies, and records. PostgreSQL holds state; local disk holds encrypted files and the ledger.",
        ),
        *table(
            ["Package", "Version", "Where it is used", "Why"],
            [
                ["Python", "3.12 container, 3.14 local", "Runtime.", "Modern typing and performance."],
                ["FastAPI", "0.115+", "HTTP routing and dependency injection.", "Typed request models, OpenAPI generation."],
                ["Uvicorn", "0.34+", "ASGI server.", "Simple, fast application server."],
                ["Pydantic", "2.10+", "Request and response schemas.", "Strict validation and serialization."],
                ["pydantic-settings", "2.7+", "Environment configuration.", "AUTHENTIQ_ prefixed settings with validation."],
                ["SQLAlchemy", "2.0+", "ORM and sessions.", "Explicit models, relationship loading, portable SQL."],
                ["psycopg", "3.2+", "PostgreSQL driver.", "Neon and Compose PostgreSQL connectivity."],
                ["python-jose", "3.3+", "JWT access and refresh tokens.", "Claims, expiry, signing."],
                ["argon2-cffi", "23.1+", "Password hashing.", "Argon2id with per-password salts."],
                ["cryptography", "44+", "AES-GCM and Fernet.", "File, evidence, idea, and secret encryption."],
                ["ReportLab", "4.2+", "PDF certificates and reports.", "Programmatic, deterministic PDFs."],
                ["qrcode", "8.0+", "Certificate QR codes.", "Offline link to the verification page."],
                ["Pillow", "11+", "QR image handling.", "Rendering and image metadata support."],
                ["httpx", "0.28+", "Outbound HTTP and Polygon JSON-RPC.", "Timeouts and a single client API."],
                ["python-multipart", "0.0.20+", "Chunk and evidence uploads.", "Multipart parsing in FastAPI."],
                ["email-validator", "2.2+", "Email normalization.", "Rejects malformed addresses."],
                ["pytest", "8.3+", "Backend test suite.", "76 integration and security tests."],
                ["pytest-asyncio", "0.25+", "Async test support.", "Exercises async code paths."],
                ["Alembic", "listed", "Schema migrations.", "Dependency is present; no revision history yet."],
            ],
            widths=[112, 72, 135, 176],
            bold_first=True,
        ),
        gap(2),
        h2("Layering"),
        *table(
            ["Layer", "Location", "Responsibility"],
            [
                ["HTTP", "app/api/", "Routing, status codes, payload validation, response shaping."],
                ["Dependencies", "app/core/deps.py", "Database session, client IP, current user, token validation."],
                ["Services", "app/services/", "Registration, access, analysis, certificates, evidence, integrity, notifications, audit, serializers."],
                ["Domain crypto", "app/zkp/, app/fingerprint/, app/security/", "Poseidon, BN254, Schnorr, SHA-256, passwords, JWTs, encryption."],
                ["Storage", "app/storage/", "AQVL1 containers, chunk handling, extension and malware gates."],
                ["Ledger", "app/ledger/", "Simulation and Polygon adapters behind one interface."],
                ["Models and schemas", "app/models/, app/schemas/", "SQLAlchemy tables and Pydantic contracts."],
                ["Configuration", "app/core/config.py", "Environment settings and path resolution."],
            ],
            widths=[100, 165, 230],
            bold_first=True,
        ),
        gap(4),
        h2("Why synchronous handlers"),
        p(
            "Hashing, encryption, proof generation, and certificate rendering are CPU- and I/O-local tasks. Synchronous handlers keep the flow readable and deterministic, and the workload is not highly concurrent. A production deployment that expects sustained load should move certificate and report generation to a worker queue and run multiple API workers behind a shared rate limiter."
        ),
        h2("Error model"),
        *table(
            ["Status", "Meaning", "Typical cause"],
            [
                ["400", "Invalid state or bad request", "Malformed transition or missing prerequisite."],
                ["401", "Missing, expired, or invalid token", "No bearer token, expired access token."],
                ["403", "Authenticated but not authorized", "Wrong owner, organization, or role."],
                ["404", "Not found or hidden by access control", "A record the caller may not see."],
                ["409", "State conflict or replay", "Usage limit reached, duplicate transition."],
                ["410", "Expired or revoked", "Share link expired, revoked, or consumed."],
                ["413 / 415", "Too large or unsupported type", "File over 200 MB or extension outside the list."],
                ["422", "Validation or integrity failure", "Chunk hash mismatch, proof mismatch."],
                ["423", "Account locked", "Too many failed logins."],
                ["429", "Rate limit exceeded", "Inspect Retry-After."],
                ["500", "Unexpected server error", "Details logged server-side, not returned."],
            ],
            widths=[64, 190, 241],
            bold_first=True,
        ),
        gap(2),
        callout(
            "One backend rule",
            "Pydantic validates shape. Services validate state. Access helpers validate relationships. None of them trusts a role or owner id supplied by the client.",
        ),
    ]


def chapter_data() -> list:
    return [
        *chapter(
            32,
            "Data layer and schema",
            "Technology",
            "Relational state lives in PostgreSQL, currently a hosted Neon database. SQLite remains the zero-setup fallback and the test database. Files and the ledger are not in the database.",
        ),
        h2("The active configuration"),
        *kv(
            [
                ("Database", "PostgreSQL on Neon, pooled connection with SSL required."),
                ("Driver", "psycopg 3 through SQLAlchemy 2."),
                ("Engine options", "pool_pre_ping=True, pool_recycle=280 seconds, connect_timeout=15 seconds."),
                ("Schema creation", "SQLAlchemy metadata at application startup. No migration revisions are stored yet."),
                ("Local fallback", "sqlite:///backend/authentiq.db when AUTHENTIQ_DATABASE_URL is unset."),
                ("Test database", "An isolated SQLite database created by the pytest fixtures."),
            ]
        ),
        gap(8),
        h2("Twenty-nine tables in five domains"),
        *table(
            ["Domain", "Tables", "Count"],
            [
                ["Identity", "users, organizations, organization_members, user_sessions, password_reset_tokens", "5"],
                ["Registrations", "registrations, file_metadata, uploads, file_chunks, commitments, zkp_challenges, zkp_proofs, verification_requests, ledger_transactions", "9"],
                ["Content", "ideas, idea_revisions, creative_versions, ai_provenance", "4"],
                ["Collaboration", "team_projects, team_members, contribution_records, ownership_allocations", "4"],
                ["Governance and operations", "ownership_transfers, theft_alerts, similarity_analyses, disputes, dispute_evidence, notifications, audit_logs", "7"],
            ],
            widths=[130, 320, 45],
            bold_first=True,
        ),
        gap(4),
        h2("What lives where"),
        *table(
            ["Data", "Location", "Backup implication"],
            [
                ["Users, registrations, metadata, proofs, teams, transfers, disputes, notifications, audit entries", "PostgreSQL", "A database backup or provider point-in-time recovery."],
                ["Encrypted original files and versions", "storage/uploads on local disk", "Must be backed up separately; the database only stores the path."],
                ["Encrypted dispute evidence", "storage/evidence on local disk", "Must be backed up with the disputes they support."],
                ["Simulation ledger", "storage/ledger.jsonl", "Append-only file; back it up with the database to preserve linkage."],
                ["Certificates", "Generated on demand", "Nothing to back up; regenerate from the record."],
            ],
            widths=[225, 135, 135],
            bold_first=True,
        ),
        gap(4),
        h2("Connection and portability"),
        p(
            "The engine is created from AUTHENTIQ_DATABASE_URL. PostgreSQL URLs are normalized to the psycopg driver. The pool is configured to survive a hosted database that closes idle connections: pre-ping checks a connection before use, recycle retires it before the provider timeout, and a 15-second connect timeout prevents a hung request. SQLite is kept for tests because it is fast, isolated, and requires no service."
        ),
        h2("Schema lifecycle"),
        p(
            "Tables are created from SQLAlchemy metadata at startup. That is convenient for a prototype and dangerous for production: it does not version changes, backfill data, or coordinate zero-downtime migrations. Alembic is listed as a dependency but no revision history is included. A real deployment should generate an initial migration, switch startup to check-only, and run migrations as a separate step."
        ),
        callout(
            "The split that surprises people",
            "A Neon backup restores users, registrations, and metadata. It does not restore encrypted files or ledger.jsonl. If the filesystem is lost, the records survive but the original bytes and the local chain do not.",
        ),
    ]


def chapter_crypto() -> list:
    story: list = [
        *chapter(
            33,
            "Cryptography",
            "Technology",
            "The cryptographic layer is small, explicit, and implemented in Python. It separates content hashing, ownership commitments, zero-knowledge proofs, password hashing, token signing, and symmetric encryption.",
        ),
        *table(
            ["Primitive", "Implementation", "Purpose", "Where"],
            [
                ["SHA-256", "Python hashlib and browser Web Crypto", "Canonical file, chunk, record, and audit hashes.", "Uploads, fingerprint API, ledger, audit, certificates."],
                ["Poseidon-254", "Pure Python with circomlib-compatible BN254 constants", "Commitment over fingerprint and secret.", "Registration and idea creation."],
                ["BN254 G1", "Pure Python curve arithmetic", "Group operations for commitments and proofs.", "ZKP and sharing."],
                ["Pedersen commitment", "C = sG + rH with s = Poseidon(fingerprint, secret)", "Hiding commitment used by the proof.", "Registration, proof generation."],
                ["Schnorr proof", "Fiat-Shamir non-interactive over BN254 G1", "Knowledge of the commitment opening.", "Proof generation and verification."],
                ["Argon2id", "argon2-cffi", "Password hashing.", "Sign-up, login, password change."],
                ["JWT", "python-jose", "Access and refresh token claims.", "Authentication."],
                ["AES-256-GCM", "cryptography", "Chunked file and evidence encryption.", "AQVL1 storage containers."],
                ["Fernet", "cryptography", "Idea descriptions, notes, commitment secrets.", "Ideas and internal secret storage."],
            ],
            widths=[88, 140, 147, 120],
            bold_first=True,
        ),
        gap(2),
        h2("The commitment"),
        p(
            "For each registration the server computes a Poseidon digest of the file fingerprint and a fresh random secret, then commits to it as sG + rH. The secret and blinding factor are stored encrypted; neither is returned to the browser. The commitment is public: it can be shown, shared, and checked without revealing the opening."
        ),
        code_block(
            [
                "s = Poseidon254(fingerprint mod p, secret)",
                "C = sG + rH",
                "proof: knowledge of (s, r) such that C = sG + rH",
            ]
        ),
        p(
            "The proof binds the registration reference, fingerprint, commitment, and a one-time nonce into the Fiat-Shamir challenge. That binding is what prevents a valid proof from being replayed against another record. The scheme identifiers are AUTHENTIQ-POSEIDON254-COMMITMENT-V1 and AUTHENTIQ-SCHNORR-BN254-G1-V1."
        ),
        h2("Verification, step by step"),
        *numbers(
            [
                "Validate the proof package shape and scheme identifier.",
                "Check that the registration reference matches the verification request.",
                "Compare the claimed fingerprint with the stored registration fingerprint.",
                "Check that the nonce matches the unused challenge and has not expired.",
                "Recompute the Fiat-Shamir challenge from the bound public signals.",
                "Evaluate the Schnorr equation against the stored commitment.",
                "Record the result, increment usage, and write an audit entry.",
            ]
        ),
        gap(2),
        h2("What the default proof does and does not establish"),
        *table(
            ["Establishes", "Does not establish"],
            [
                ["The prover knows the opening of the stored commitment.", "That the prover is the legal author."],
                ["The proof is fresh and bound to this registration and nonce.", "That the file is original or non-infringing."],
                ["The presented fingerprint matches the registered fingerprint, checked outside the circuit.", "That the fingerprint equality is constrained inside a zero-knowledge circuit."],
                ["A verifier can check the claim without receiving the file or secret.", "That the ledger timestamp is independently witnessed."],
            ],
            widths=[247, 247],
        ),
        gap(2),
        h2("Symmetric encryption and secrets"),
        p(
            "Completed files are written as AQVL1 containers: chunked AES-256-GCM with a per-chunk nonce and authentication tag. The encryption key is derived deterministically from AUTHENTIQ_SECRET_KEY. Idea descriptions, notes, and commitment secrets use Fernet text fields. The distinction matters: AQVL1 protects large binary files, Fernet protects small database text values."
        ),
        p(
            "The secret key is the root of both token signing and encryption-key derivation. Rotating it without a migration would make old files unreadable and old tokens invalid. In production, use a managed secret with a documented rotation and re-encryption plan."
        ),
        h2("Passwords and tokens"),
        *bullets(
            [
                "Passwords are hashed with Argon2id and a per-password salt; plaintext is never stored or logged.",
                "Access tokens last 45 minutes and carry user, session, role, and organization claims.",
                "Refresh tokens last 14 days, are stored hashed, and rotate on every refresh. Reuse of a consumed token fails.",
                "Password reset tokens last 30 minutes and are single-use.",
                "A password change revokes every session.",
            ]
        ),
        callout(
            "The sentence to keep",
            "The default proof proves knowledge of the commitment opening. File-hash equality is verified separately before proving and during verification; it is not constrained inside the default circuit.",
        ),
        h2("The optional Circom circuit"),
        p(
            "circuits/ownership.circom proves commitment = Poseidon(fingerprint mod p, secret) with Circom 2.1.6, Circomlib 2.0.5, and snarkjs 0.7.5. It is a reference for a future Groth16 integration and is not wired into runtime proof generation or verification. The shipped runtime proof remains the Schnorr scheme."
        ),
    ]
    return story


def chapter_blockchain() -> list:
    return [
        *chapter(
            34,
            "Blockchain and ledger tooling",
            "Technology",
            "The default ledger is a local append-only JSONL simulation. Polygon Amoy is an optional adapter that writes real testnet transactions. The product never calls the simulation a blockchain.",
        ),
        h2("The simulation record"),
        *table(
            ["Field", "Meaning"],
            [
                ["block_number", "Monotonic position in the local chain."],
                ["prev_hash", "Record hash of the previous entry."],
                ["record_hash", "SHA-256 over the canonical record body."],
                ["payload_digest", "SHA-256 of the canonical event payload."],
                ["tx_id", "Application-level transaction identifier."],
                ["type", "registration, proof, transfer, team, dispute, idea, and related events."],
                ["actor_id and actor_ref", "Who caused the event."],
                ["entity_type and entity_id", "What the event is about."],
                ["timestamp", "UTC creation time."],
                ["network", "AUTHENTIQ Local Ledger by default."],
            ],
            widths=[150, 345],
            bold_first=True,
        ),
        gap(2),
        h2("How chain verification works"),
        *numbers(
            [
                "Read the JSONL file in order.",
                "Recompute each record hash from its canonical body.",
                "Check that each prev_hash equals the previous record hash.",
                "Check that each block number increases by one.",
                "Recompute each payload digest and compare it with the stored value.",
                "Report the first mismatch with its block number and reason.",
            ]
        ),
        gap(2),
        p(
            "Appending calls fsync after writing the line, which reduces the chance of losing the tail on a crash. It does not make the file immutable. An operator with filesystem access can rewrite the whole chain, so verification is a detection mechanism, not a distributed trust guarantee."
        ),
        h2("The Polygon Amoy adapter"),
        p(
            "When AUTHENTIQ_LEDGER_MODE=polygon and the RPC URL, private key, contract address, and chain ID are configured, the adapter calls recordEvent(recordId, recordType, payloadDigest, entityId) on the Solidity registry, waits for a receipt, and returns the real transaction hash and block number. If configuration or connectivity fails, the operation fails with a clear error; it never silently falls back to simulation."
        ),
        *table(
            ["Component", "Version or role", "Where"],
            [
                ["Solidity", "0.8.24", "blockchain/contracts/AuthentiqRegistry.sol"],
                ["Hardhat", "2.22", "Compile, test, and deploy."],
                ["Polygon Amoy", "Chain ID 80002", "Public testnet target."],
                ["web3.py", "Optional package", "JSON-RPC and contract calls in the adapter."],
                ["eth-account", "Optional package", "Transaction signing."],
                ["Amoy explorer", "amoy.polygonscan.com", "Human inspection of testnet transactions."],
            ],
            widths=[120, 165, 210],
            bold_first=True,
        ),
        gap(2),
        h2("Simulation, testnet, and mainnet are not the same"),
        *table(
            ["Property", "Local simulation", "Polygon Amoy", "Public mainnet"],
            [
                ["Who can rewrite history", "Anyone with filesystem access", "Amoy validators and the contract writer", "Mainnet consensus"],
                ["Cost", "Free", "Testnet gas", "Real gas"],
                ["Privacy", "Local file only", "Public testnet transaction", "Public permanent transaction"],
                ["Independence", "None", "Third-party testnet", "Strong public settlement"],
                ["Used by default", "Yes", "No, opt-in", "No"],
            ],
            widths=[112, 130, 130, 122],
            bold_first=True,
        ),
        callout(
            "The honest label",
            "A local hash-chained file is an append-only ledger simulation. It is tamper-evident and useful for a prototype. It is not distributed consensus, and the interface must never imply otherwise.",
        ),
        h2("Enabling the adapter"),
        *numbers(
            [
                "Deploy AuthentiqRegistry.sol with Hardhat.",
                "Authorize the backend signing address as a writer if it differs from the deployer.",
                "Install web3 and eth-account in the backend environment.",
                "Set ledger mode to polygon, plus RPC URL, private key, contract address, and chain ID 80002.",
                "Restart the API and check GET /api/ledger/status for connectivity and mode.",
            ]
        ),
        gap(2),
        p(
            "Amoy is a public testnet. Transactions are real testnet transactions, not mainnet settlement. The optional Circom circuit is also not wired into runtime: it proves the Poseidon relation for a future Groth16 integration, while the shipped proof remains Schnorr."
        ),
    ]


def chapter_files() -> list:
    return [
        *chapter(
            35,
            "Files, PDFs, and QR codes",
            "Technology",
            "The file pipeline is where most trust products become vague. Here is the exact path from a selected file to an encrypted container, a certificate, and a portable evidence packet.",
        ),
        h2("Upload and storage path"),
        *numbers(
            [
                "The browser slices the file into chunks of at most 8 MB.",
                "Each chunk is hashed and posted; the server checks the hash and size, writes it temporarily, and records the digest.",
                "Completion re-hashes the chunks, assembles the file, compares the overall SHA-256, and runs the scanner gate.",
                "The assembled file is encrypted into an AQVL1 container with chunked AES-256-GCM, then the temporary chunks are deleted.",
                "The database stores the registration, metadata, digests, commitments, and the storage path.",
            ]
        ),
        gap(2),
        h2("The AQVL1 container"),
        *kv(
            [
                ("Magic and version", "AQVL1 prefix, so the format can evolve explicitly."),
                ("Cipher", "AES-256-GCM with a per-chunk nonce and authentication tag."),
                ("Key", "Derived deterministically from AUTHENTIQ_SECRET_KEY."),
                ("Integrity", "Each chunk is authenticated; a modified container fails decryption."),
                ("Temporary state", "Plaintext chunks exist between chunk upload and completion, then are deleted."),
                ("Evidence", "Dispute evidence uses the same container pattern under storage/evidence."),
            ]
        ),
        gap(8),
        h2("The certificate"),
        p(
            "Certificates are generated on demand with ReportLab and are not cached. The PDF uses the house design system and contains the registration reference, title, owner display name, SHA-256 fingerprint, Poseidon and Pedersen commitments, registration timestamp, ledger transaction, a simulation or chain-mode label, and a QR code that points to the public verification page."
        ),
        *bullets(
            [
                "The QR code is useful only while the verification link or record remains accessible.",
                "The certificate states what the record is, not what a court should conclude.",
                "A version certificate and a team certificate use the same generators with their own fields.",
                "Regenerating after a change produces a current document; there is no stale cached copy.",
            ]
        ),
        h2("The evidence packet"),
        *table(
            ["File", "Contents", "Why it is there"],
            [
                ["manifest.json", "Canonical registration, file metadata, ledger receipt, proofs, trust score and factors, self-hash.", "The machine-readable core of the packet."],
                ["certificate.pdf", "The rendered certificate for the record.", "A human-readable artifact."],
                ["ledger-receipt.json", "Block number, record hash, previous hash, payload digest.", "Lets a reviewer compare the record with the chain."],
                ["file.sha256.txt", "The digest in sha256sum-compatible form.", "Offline byte verification."],
                ["VERIFY.txt", "Step-by-step instructions, including recomputing the manifest hash.", "Makes the packet self-describing."],
            ],
            widths=[100, 245, 150],
            bold_first=True,
        ),
        gap(2),
        callout(
            "What the packet does not contain",
            "The original file, the commitment secret, the password, or a private key. It is evidence about a record, not a copy of the vault.",
        ),
        h2("Storage directories"),
        *table(
            ["Path", "Contents"],
            [
                ["storage/uploads/", "Encrypted AQVL1 containers and temporary chunk directories."],
                ["storage/evidence/", "Encrypted dispute evidence grouped by dispute."],
                ["storage/ledger.jsonl", "The append-only simulation ledger."],
                ["backend/authentiq.db", "SQLite fallback database when PostgreSQL is not configured."],
            ],
            widths=[170, 325],
            bold_first=True,
        ),
        h2("Retention and backup"),
        p(
            "There is no automatic retention or deletion policy. Files remain until an operator removes them. Because the database stores paths rather than bytes, a restore that only covers PostgreSQL leaves records pointing at missing files. Back up the database, the upload and evidence directories, and ledger.jsonl together, and test a restore before relying on it."
        ),
    ]


def chapter_infra() -> list:
    return [
        *chapter(
            36,
            "Infrastructure, documentation, and configuration",
            "Technology",
            "The last technical chapter covers how the product is served, tested, configured, and documented. It is the layer that makes the rest reproducible.",
        ),
        h2("Serving and orchestration"),
        *table(
            ["Tool", "Role", "Notes"],
            [
                ["Vite", "Development server and production bundle.", "Port 5173 in development; /api proxies to 8000."],
                ["Nginx", "Static SPA serving, history fallback, /api reverse proxy.", "Port 8080 in Compose."],
                ["Docker", "Backend and frontend images.", "Reproducible runtime."],
                ["Docker Compose", "PostgreSQL 16, backend, frontend, health checks, volumes.", "Backend waits for the database health check."],
                ["Uvicorn", "ASGI server.", "Single worker recommended with the in-process limiter."],
                ["pytest", "Backend verification.", "76 tests across auth, uploads, ZKP, ledger, audit, teams, transfers, disputes, dashboard, organization member provisioning, and audit chain concurrency."],
                ["TypeScript and Vite build", "Frontend verification.", "tsc --noEmit then vite build."],
                ["Hardhat", "Optional Solidity tooling.", "Compile, test, deploy the registry."],
            ],
            widths=[112, 190, 193],
            bold_first=True,
        ),
        gap(2),
        h2("Commands"),
        code_block(
            [
                "cd backend",
                ".venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000",
                ".venv\\Scripts\\python.exe -m pytest -q",
                ".venv\\Scripts\\python.exe -m app.seed",
                "",
                "cd frontend",
                "npm install",
                "npm run dev",
                "npm run build",
            ]
        ),
        gap(4),
        h2("Configuration reference"),
        *table(
            ["Variable", "Purpose", "Default"],
            [
                ["AUTHENTIQ_SECRET_KEY", "JWT signing and encryption key derivation.", "Development placeholder"],
                ["AUTHENTIQ_DATABASE_URL", "SQLAlchemy URL.", "SQLite at backend/authentiq.db"],
                ["AUTHENTIQ_STORAGE_DIR", "Storage root.", "storage/"],
                ["AUTHENTIQ_UPLOAD_DIR", "Encrypted uploads.", "storage/uploads"],
                ["AUTHENTIQ_EVIDENCE_DIR", "Encrypted evidence.", "storage/evidence"],
                ["AUTHENTIQ_LEDGER_FILE", "Simulation ledger path.", "storage/ledger.jsonl"],
                ["AUTHENTIQ_LEDGER_MODE", "simulation or polygon.", "simulation"],
                ["AUTHENTIQ_CHAIN_RPC_URL", "Polygon RPC endpoint.", "Empty"],
                ["AUTHENTIQ_CHAIN_PRIVATE_KEY", "Writer key for the registry.", "Empty"],
                ["AUTHENTIQ_CHAIN_CONTRACT_ADDRESS", "Registry address.", "Empty"],
                ["AUTHENTIQ_CHAIN_ID", "Amoy chain ID.", "80002"],
                ["AUTHENTIQ_ZKP_CHALLENGE_MINUTES", "Challenge lifetime.", "10"],
                ["AUTHENTIQ_ZKP_VERIFICATION_HOURS", "Share lifetime bound.", "72"],
                ["AUTHENTIQ_MAX_FILE_SIZE_MB", "Upload cap.", "200"],
                ["AUTHENTIQ_MAX_CHUNK_SIZE_MB", "Chunk cap.", "8"],
                ["AUTHENTIQ_CORS_ORIGINS", "Allowed browser origins.", "Local Vite origins"],
                ["AUTHENTIQ_PUBLIC_APP_URL", "Verification link base.", "http://localhost:5173"],
                ["AUTHENTIQ_SEED_DEMO", "Create demo accounts at startup.", "false"],
            ],
            widths=[205, 200, 90],
            bold_first=True,
        ),
        gap(2),
        h2("Documentation set"),
        *table(
            ["Document", "What it covers"],
            [
                ["README.md", "Product summary, implemented capabilities, quick start, demo accounts, stack, limitations."],
                ["docs/ARCHITECTURE.md", "Components, flows, data model, ledger, audit, authorization, deployment, failure behavior."],
                ["docs/TECH_STACK.md", "Versions, rationale, storage formats, cryptography, intentional omissions."],
                ["docs/API.md", "Endpoint tables, payloads, status codes, rate limits, integrity and trust endpoints."],
                ["docs/SECURITY.md", "Threat model, controls, residual risks, disclosure policy."],
                ["docs/ZKP.md", "Exact proof statement, protocol, verification, limitations."],
                ["blockchain/README.md", "Contract, Hardhat, Amoy deployment."],
                ["circuits/README.md", "Optional Circom circuit and why it is not runtime."],
            ],
            widths=[160, 335],
            bold_first=True,
        ),
        gap(2),
        h2("Deliberate omissions"),
        *bullets(
            [
                "No external identity provider; identity is local.",
                "No email delivery provider; development tokens are returned outside production.",
                "No object storage SDK; files live on the local filesystem.",
                "No Redis or distributed cache; rate limiting is in-process.",
                "No background task queue; certificates and hashing are synchronous.",
                "No production migration pipeline.",
                "No on-chain proof verification and no Groth16 runtime integration.",
            ]
        ),
        callout(
            "Why list omissions in a handbook",
            "Because a reader who discovers them later will distrust everything else. Naming them here makes the boundary of the product legible and gives the next engineer a real backlog.",
        ),
    ]


def part_four_story() -> list:
    story: list = [
        *part_four(),
        *chapter_frontend(),
        *chapter_browser_storage(),
        *chapter_backend(),
        *chapter_data(),
        *chapter_crypto(),
        *chapter_blockchain(),
        *chapter_files(),
        *chapter_infra(),
    ]
    return story
