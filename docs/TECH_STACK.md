# AUTHENTIQ technology stack

## 1. Summary

AUTHENTIQ uses a conventional three-tier web architecture with a cryptography-heavy backend:

- React and TypeScript for the browser workspace.
- FastAPI and SQLAlchemy for the authenticated API and persistence.
- SQLite for zero-setup local use, PostgreSQL for container and production-like deployments.
- Pure-Python BN254/Poseidon/Schnorr cryptography for portable, auditable zero-knowledge proofs.
- AES-256-GCM and Fernet for data at rest.
- A ledger adapter with an append-only local simulation and an optional Polygon Amoy implementation.

No component is mocked. Where a capability depends on external infrastructure, such as email or image classifiers, the API reports that it is unavailable rather than returning fabricated results.

## 2. Frontend

| Technology | Version | Use |
| --- | --- | --- |
| React | 18.3 | Component model and UI runtime |
| React DOM | 18.3 | Browser rendering |
| TypeScript | 5.7 | Static typing |
| Vite | 6.0 | Development server and production bundling |
| React Router | 6.28 | Public and protected route tree |
| TanStack Query | 5.62 | Server-state caching, mutations, invalidation |
| React Hook Form | 7.54 | Form state and validation integration |
| Zod | 3.24 | Schema validation |
| Tailwind CSS | 3.4 | Utility-first styling and design tokens |
| Radix UI | 1.x / 2.x | Accessible dialog, dropdown, label, tabs, and slot primitives |
| class-variance-authority | 0.7 | Component variants |
| Tailwind Merge | 2.6 | Conflict-free class composition |
| Lucide React | 0.468 | Icons |
| Recharts | 2.15 | Dashboard and analytics charts |
| Framer Motion | 11.15 | Page and component transitions |
| Sonner | 1.7 | Toast notifications |
| date-fns | 4.1 | Date formatting |
| Funnel Display | woff2 | Interface and body type face, self-hosted |
| Turret Road | woff2 | Display type face for headings, self-hosted |

### Design system

The landing page stylesheet in `frontend/src/styles/landing.css` is loaded before the application stylesheet, so one stylesheet defines the whole product.

| Token | Value | Meaning |
| --- | --- | --- |
| `--paper` | `#FFFFFF` | Page background |
| `--light` | `#EAEAEA` | Secondary surface |
| `--dark` | `#171717` | Ink, borders, primary text |
| `--lime` | `#B7FF00` | Accent, focus ring, highlights |
| `--muted-foreground` | `#888888` | Secondary text, dividers, inactive states |
| `--border` | `#D0D0D0` | Card edges and rules |
| `--warning` | `#454545` | Dark grey for caution states |

`Funnel Display` carries body and interface copy. `Turret Road` carries display headings and is uppercased where the landing design requires it. Both fonts are self-hosted woff2 files in `frontend/public/fonts`, so no third-party font request leaves the machine.

The Tailwind theme maps the same palette onto semantic tokens and remaps the legacy blue, indigo, violet, emerald, and slate scales onto ink, lime, and the neutral greys so the workspace screens inherit the landing page's identity without per-component overrides. No other hue is used anywhere in the product.

### Why this frontend stack

- Vite keeps local startup fast and produces a static bundle that Nginx can serve.
- TanStack Query separates server state from local UI state and makes cache invalidation explicit after mutations.
- React Hook Form plus Zod keeps validation rules close to forms while the backend remains authoritative.
- Radix primitives provide keyboard and focus behaviour without adopting a large component framework.
- Tailwind and CSS variables carry the single house theme, so there is no runtime style system and no second colour set to drift.

### Frontend conventions

- `src/lib/api.ts` is the only HTTP entry point. It handles bearer tokens, single-flight refresh, retries, error extraction, blob downloads, and SHA-256 helpers.
- `src/lib/upload.ts` implements chunked uploads and per-chunk hashing.
- `src/context/AuthContext.tsx` restores sessions and exposes login/logout state.
- `src/components/layout/AppShell.tsx` owns navigation, global search, notifications, ledger status, and the user menu.
- Protected routes render through `ProtectedShell`, which redirects unauthenticated users to `/login` with the attempted path.
- The verification page `/verify/:verificationId` is public and does not require a session.

### Browser cryptography

The browser uses `crypto.subtle.digest("SHA-256", ...)` to hash files locally before upload. The server independently recomputes the digest. The browser hash is evidence of client-side integrity, not a substitute for server verification.

## 3. Backend

| Technology | Version | Use |
| --- | --- | --- |
| Python | 3.12 in container; 3.14 used for local verification | Runtime |
| FastAPI | 0.115+ | HTTP API, dependency injection, OpenAPI |
| Uvicorn | 0.34+ | ASGI server |
| Pydantic | 2.10+ | Request/response validation and settings |
| pydantic-settings | 2.7+ | Environment configuration |
| SQLAlchemy | 2.0+ | ORM and session management |
| SQLite | Bundled | Default local database |
| PostgreSQL | 16 in Compose | Production-like database |
| psycopg | 3.2+ | PostgreSQL driver |
| python-jose | 3.3+ | JWT access and refresh tokens |
| argon2-cffi | 23.1+ | Argon2id password hashing |
| cryptography | 44+ | AES-GCM, Fernet, key derivation primitives |
| ReportLab | 4.2+ | PDF certificates and reports |
| qrcode | 8.0+ | Certificate QR codes |
| Pillow | 11+ | QR image generation and demo assets |
| httpx | 0.28+ | Polygon JSON-RPC and outbound HTTP |
| python-multipart | 0.0.20+ | Multipart uploads and evidence |
| email-validator | 2.2+ | Email normalization |
| pytest | 8.3+ | Test runner |
| pytest-asyncio | 0.25+ | Async test support |

### Why FastAPI

- Pydantic request models give strict, documented payload validation.
- Dependency injection centralizes database sessions and authenticated users.
- OpenAPI generation provides a live API contract at `/api/docs`.
- Synchronous route handlers keep file hashing, encryption, and proof generation straightforward; the workload is I/O- and CPU-local rather than highly concurrent.

### Backend layering

| Layer | Location | Responsibility |
| --- | --- | --- |
| HTTP | `app/api/` | Routing, status codes, request validation, response shaping |
| Dependencies | `app/core/deps.py` | Current user, client IP, database session |
| Services | `app/services/` | Registration, audit, access control, certificates, notifications, serialization |
| Domain crypto | `app/zkp/`, `app/fingerprint/`, `app/security/` | Poseidon, BN254, Schnorr, SHA-256, chunk hashing, passwords, tokens |
| Storage | `app/storage/` | Encrypted file containers, scanner gate |
| Ledger | `app/ledger/` | Simulation and Polygon adapters |
| Models | `app/models/` | SQLAlchemy tables and relationships |
| Schemas | `app/schemas/` | Pydantic contracts |
| Configuration | `app/core/config.py` | `AUTHENTIQ_` settings and path resolution |

## 4. Data and storage

### SQLite default

The default URL is `sqlite:///backend/authentiq.db`. SQLite is suitable for local evaluation and single-node use. It is not intended for multi-writer production deployments.

### PostgreSQL

Set:

```text
AUTHENTIQ_DATABASE_URL=postgresql+psycopg://user:password@host:5432/authentiq
```

Docker Compose provisions PostgreSQL 16 with a health check and a persistent named volume.

### Tables

The schema contains 29 application tables covering identity, uploads, registrations, proofs, sharing, ideas, versions, provenance, teams, transfers, alerts, disputes, notifications, ledger metadata, and audit events. Tables are created from SQLAlchemy metadata at startup. Alembic is listed as a dependency but no migration revision history is included yet.

### Organization provisioning

Organization administrators create member accounts through `POST /api/settings/organization/members`. The API validates the email address, rejects duplicates case-insensitively, generates a 16-character password with lowercase, uppercase, digit, and symbol characters, and stores only the Argon2id hash. The account and an active `OrganizationMember` row are created in one transaction, and the plaintext password is returned once under `credentials.password`. Email delivery is not configured, so the administrator copies the credentials manually.

`POST /api/settings/organization/members/{member_id}/password` rotates a member password, clears lockout counters, and revokes every active session for that user. Both actions write append-only audit events and are limited to the organization owner or an `org_admin`. Legacy `org_admin` accounts without an organization are assigned one lazily so the provisioning UI remains usable.

### File formats

- **Upload container:** `AQVL1`, chunked AES-256-GCM with per-chunk nonces and authentication tags.
- **Temporary chunks:** plaintext files under `storage/uploads/chunks/{upload_id}` until completion; deleted after encryption.
- **Evidence:** encrypted `AQVL1` containers under `storage/evidence/{dispute_id}`.
- **Simulation ledger:** canonical JSON Lines, one record per line, with a hash chain.
- **Certificates:** PDF generated on demand; not cached on disk.

## 5. Cryptography

| Primitive | Implementation | Purpose |
| --- | --- | --- |
| SHA-256 | Python `hashlib`, browser Web Crypto | Canonical file and chunk fingerprints |
| Poseidon-254 | Pure Python, circomlib-compatible BN254 constants | Commitment over fingerprint and secret |
| BN254 G1 | Pure Python curve arithmetic | Pedersen commitments and Schnorr proofs |
| Pedersen commitment | `C = sG + rH`, `s = Poseidon(fingerprint, secret)` | Hiding commitment used by the proof |
| Schnorr proof | Fiat-Shamir non-interactive proof over BN254 G1 | Knowledge of commitment opening |
| AES-256-GCM | `cryptography` library | File and evidence encryption at rest |
| Fernet | `cryptography` library | Idea descriptions, notes, commitment secrets |
| Argon2id | `argon2-cffi` | Password hashing |
| JWT | `python-jose` | Short-lived access tokens, refresh tokens, reset tokens |

The scheme identifier is `AUTHENTIQ-SCHNORR-BN254-G1-V1`. The Poseidon scheme identifier is `AUTHENTIQ-POSEIDON254-COMMITMENT-V1`.

The optional Circom circuit uses Circom 2.1.6, Circomlib 2.0.5, and snarkjs 0.7.5. It is not part of the runtime.

## 6. Ledger and chain tooling

| Technology | Use |
| --- | --- |
| JSONL simulation | Default append-only local ledger with SHA-256 record chaining |
| Solidity 0.8.24 | `AuthentiqRegistry` ownership event registry |
| Hardhat 2.22 | Compile, test, and deploy the contract |
| Polygon Amoy | Public testnet target for real testnet transactions |
| web3.py / eth-account | Optional Python packages used by the Polygon adapter |

The backend ABI call is `recordEvent(string recordId, string recordType, string payloadDigest, string entityId)`. The contract stores the latest record per identifier and an event history. Authorization is writer-based.

## 7. Infrastructure and tooling

| Technology | Use |
| --- | --- |
| Docker | Reproducible backend and frontend images |
| Docker Compose | PostgreSQL, backend, frontend, health checks, volumes |
| Nginx | Static SPA serving, history fallback, `/api` reverse proxy |
| pytest | Backend integration and security tests |
| TypeScript compiler | Build-time type checking |
| Vite build | Production frontend bundle |
| Hardhat tests | Solidity contract tests |

The Compose topology is:

```text
Browser -> Nginx :8080 -> static SPA
                      -> /api -> FastAPI :8000 -> PostgreSQL :5432
                                              -> /data volume
```

## 8. Configuration model

All backend settings use the `AUTHENTIQ_` prefix and are loaded from the root `.env` or `backend/.env`:

```text
AUTHENTIQ_SECRET_KEY
AUTHENTIQ_DATABASE_URL
AUTHENTIQ_STORAGE_DIR
AUTHENTIQ_UPLOAD_DIR
AUTHENTIQ_EVIDENCE_DIR
AUTHENTIQ_LEDGER_FILE
AUTHENTIQ_LEDGER_MODE
AUTHENTIQ_CHAIN_RPC_URL
AUTHENTIQ_CHAIN_PRIVATE_KEY
AUTHENTIQ_CHAIN_CONTRACT_ADDRESS
AUTHENTIQ_CHAIN_ID
AUTHENTIQ_ZKP_CHALLENGE_MINUTES
AUTHENTIQ_ZKP_VERIFICATION_HOURS
AUTHENTIQ_MAX_FILE_SIZE_MB
AUTHENTIQ_MAX_CHUNK_SIZE_MB
AUTHENTIQ_CORS_ORIGINS
AUTHENTIQ_PUBLIC_APP_URL
AUTHENTIQ_SEED_DEMO
```

The frontend uses `VITE_API_URL`, which defaults to `/api`. Vite development proxies `/api` to `http://localhost:8000`.

## 9. Deliberate omissions

- No external authentication provider; identity is local.
- No email delivery provider; development tokens are returned in responses outside production.
- No object storage SDK; local filesystem storage is used.
- No Redis or distributed cache; rate limiting and notification state are in-process or database-backed.
- No background task queue; long operations are synchronous.
- No production migration pipeline.
- No on-chain proof verification.
- No Groth16 runtime integration.

These omissions are documented in the README and security model so that the project does not overstate its production readiness.
