# AUTHENTIQ

AUTHENTIQ is a full-stack digital notary and intellectual-property protection workspace. It records cryptographic fingerprints of creative work, generates real zero-knowledge ownership proofs, maintains an append-only audit trail, and provides privacy-preserving verification links without exposing original files or private commitment secrets.

The site opens at `/` on the AUTHENTIQ landing page. `/login` is the sign-in for the workspace. `/verify` is the public, anonymous ownership verifier and requires no account.

> AUTHENTIQ is a working engineering prototype, not a law firm, a court, or a production custody service. Registration priority is evidence, not an automatic legal determination of authorship. The default ledger is an append-only simulation, clearly labelled as simulated throughout the UI and API. Polygon Amoy can be enabled for real testnet transactions.

## What is implemented

| Area | Capability |
| --- | --- |
| Landing page | AUTHENTIQ marketing site on the house design system: Funnel Display and Turret Road type, ink and lime palette, animated liquid cursor, sectioned product narrative |
| Authentication | Argon2id passwords, JWT access and refresh tokens, session records, refresh rotation, logout, account lockout, IP/account rate limiting, password reset tokens, session revocation |
| Accounts | Individual and organization accounts, organization admin roles, organization member provisioning with one-time generated passwords, member password rotation with session revocation, profile settings, demo accounts |
| File intake | SHA-256 canonical fingerprint, browser-side hashing, chunked uploads, per-chunk SHA-256 verification, overall SHA-256 comparison, extension allow-list, size limits, malware-scanner gate |
| Storage | Chunked AES-256-GCM encryption at rest for uploads and dispute evidence, Fernet-encrypted idea descriptions and commitment secrets |
| Registrations | Ownership registration, metadata, privacy modes, pre-upload duplicate detection by SHA-256 and image perceptual hash, similar-title alerts, PDF certificates with QR codes, provenance records |
| Zero-knowledge proofs | BN254 Poseidon commitments, Pedersen commitments, non-interactive Schnorr proofs, Fiat-Shamir binding, challenge expiry, replay prevention |
| Sharing | Silent-sharing verification links, disclosure controls, expiry, maximum uses, public proof verification, revocation |
| Public verification | Login-free `/verify` page: registration reference, creator-issued private verification key, local file hashing, server challenge, browser-generated BN254 Schnorr proof, verification checklist |
| Ideas | Private/timestamp-only/organization idea vault, encrypted descriptions, Poseidon commitments, revisions, reveal, certificates, evidence packages |
| Creative history | Version timeline, per-version fingerprints, version comparison, version certificates |
| Teams | Team projects, email invitations with one-time invite codes, code redemption, join requests, contributions, unanimous 100% ownership allocation, team certificates |
| Transfers | Two-party ownership transfers with recipient acceptance, rejection, cancellation, owner confirmation, append-only chain of ownership, incoming-ownership visibility, and private credential rotation on completion |
| Organization | Organization workspaces with the same invite-and-accept flow as teams, member roles, shareable invite codes, per-registration organization ownership, and a dedicated organization page for members and registrations |
| Site administration | Website-wide control center for the `site_admin` role: accounts, roles, suspensions, disputes, organizations, teams, registrations, and the audit trail |
| Disputes | Dispute lifecycle, encrypted evidence upload, verifier/org-admin review, evidence reports, earliest-registration priority evidence |
| Alerts | Duplicate and similarity alerts, status workflow, investigation notes |
| Integrity center | Live ledger and audit chain verification, storage and ledger linkage checks, workspace snapshot digest, record-level ledger map |
| Evidence packets | One-click ZIP with certificate, canonical manifest, ledger receipt, file digest, verification instructions, and a trust score |
| Ownership trust | Explainable 0-100 evidence score, deterministic ownership DNA grid rendered from the SHA-256 fingerprint, downloadable SVG |
| Ledger | Append-only JSONL simulation with hash chaining, tamper audit, transaction inspection; optional Polygon Amoy adapter |
| Audit | Append-only hash-chained audit log for security-relevant actions, chain verification endpoint |
| Operations | Notification inbox, dashboard metrics, global search, health endpoint, structured OpenAPI docs, Docker Compose, pytest suite |

## Architecture at a glance

```mermaid
flowchart LR
    B[Browser / React SPA] -->|HTTPS JSON + multipart| API[FastAPI REST API]
    API --> AUTH[Auth, RBAC, rate limits]
    API --> DB[(SQLite or PostgreSQL)]
    API --> FS[(Encrypted file storage)]
    API --> LEDGER[Ledger adapter]
    LEDGER --> SIM[JSONL simulation ledger]
    LEDGER --> POLY[Polygon Amoy registry]
    API --> ZKP[Poseidon + BN254 Schnorr]
    API --> AUDIT[Hash-chained audit log]
```

The browser never receives private commitment secrets. The server derives the witness when a proof or share link is requested, verifies file fingerprints separately, and records the verification event.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Technology

- **Frontend:** React 18, TypeScript, Vite 6, React Router, TanStack Query, React Hook Form, Zod, Tailwind CSS, Radix UI primitives, Recharts, Framer Motion, Sonner.
- **Design system:** Turret Road for display type, Funnel Display for interface and body copy. Ink `#171717`, off-white `#EAEAEA`, white `#FFFFFF`, greys `#454545`, `#888888`, `#D0D0D0`, and neon lime `#B7FF00`. The landing page stylesheet is the source of the palette and is shared with the workspace.
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Uvicorn, Argon2id, python-jose, ReportLab, qrcode, cryptography, httpx.
- **Data:** SQLite for local development, PostgreSQL supported through `AUTHENTIQ_DATABASE_URL`.
- **Cryptography:** SHA-256, Poseidon-254 with circomlib-compatible BN254 constants, BN254 G1 arithmetic, Pedersen commitments, Schnorr proofs, AES-256-GCM, Fernet.
- **Optional chain:** Solidity 0.8.24 registry, Hardhat, Polygon Amoy.
- **Optional circuit:** Circom 2.1.6 / Circomlib ownership circuit, not wired into runtime.

Full rationale and versions: [docs/TECH_STACK.md](docs/TECH_STACK.md).

## Repository layout

```text
AUTHENTIQ/
  backend/          FastAPI application, models, services, crypto, tests
  frontend/         React single-page application, landing page, and design tokens
  blockchain/       Optional Solidity registry and Hardhat deployment
  circuits/         Optional Circom ownership circuit
  docs/             Architecture, stack, API, security, and ZKP documentation
  storage/          Local uploads, evidence, and simulation ledger
  docker-compose.yml
  .env.example
```

## Quick start

### Prerequisites

- Python 3.11 or newer. Local verification used Python 3.14; the container uses Python 3.12.
- Node.js 20 or newer.
- npm.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The API is at `http://localhost:8000`, health at `http://localhost:8000/api/health`, and OpenAPI docs at `http://localhost:8000/api/docs`.

SQLite is used by default at `backend/authentiq.db`. No database server is required. To use a hosted PostgreSQL instance such as Neon, set `AUTHENTIQ_DATABASE_URL=postgresql://user:password@host/db?sslmode=require` in `backend/.env`. Tables are created on startup and `python -m app.seed` writes the three demo accounts. The bundled `.env` in this workspace already points at the Neon database, so the running API persists to PostgreSQL.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The landing page is at `/`, the workspace sign-in is at `/login`. Vite proxies `/api` to `http://localhost:8000`.

### 3. Demo login accounts

The seed creates only the three demo login accounts. It does not create registrations, ideas, teams, alerts, transfers, disputes, verification links, ledger records, or audit events. Every workspace starts empty.

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.seed
```

The seed is idempotent: existing accounts are left untouched. To create the accounts automatically on API startup, set `AUTHENTIQ_SEED_DEMO=true`.

### Demo credentials

| Role | Email | Password |
| --- | --- | --- |
| Organization admin | `demo@authentiq.dev` | `Authentiq!Demo2026` |
| Verifier | `verifier@authentiq.dev` | `Authentiq!Verify2026` |
| Creator / collaborator | `maya@authentiq.dev` | `Authentiq!Team2026` |

The login screen can fill these credentials. Demo accounts and records are explicitly marked `is_demo`.

## Public anonymous verification

Open `http://localhost:5173/verify` (or `/verify` on the deployed frontend). No account, login, or workspace session is involved.

1. Enter the registration reference printed on the certificate, for example `AQ-2026-1A2B3C4D`.
2. Paste the **private verification key** issued when the creation was registered. The key has the form `aqv1_<opening>_<blinding>` and can be revealed again from the signed-in registration record or the registration success screen.
3. Select the exact original file. The browser computes its SHA-256 locally; the file is never uploaded.
4. AUTHENTIQ checks the fingerprint, issues a single-use challenge, and the browser generates a BN254 Schnorr proof from the private key.
5. The server verifies the proof and returns the checklist: registration exists, fingerprint matches, challenge valid, proof valid, private key disclosed **no**, login required **no**.

The registration ID identifies the record, the SHA-256 identifies the file, and the private key proves knowledge of the commitment opening. The public fingerprint is never accepted as a private credential. The key never leaves the browser: only the proof transcript is submitted. The endpoints are `POST /api/public/verify/anonymous/challenge` and `POST /api/public/verify/anonymous/verify`.

## Ownership handover

A creation can be handed to another account from **Transfers**. The flow is recipient acceptance, then owner confirmation, and both steps are written to the audit trail.

| Stage | Who owns the record | What the recipient sees |
| --- | --- | --- |
| Transfer proposed | Current owner | Read access to the record, the decrypted original, the metadata, and the proof history |
| Recipient accepted | Current owner | The same, flagged as **incoming ownership** in the dashboard, the timeline, and the record itself |
| Owner confirmed | Recipient | Full ownership: file, file data, versions, proofs, certificate, evidence packet, and a fresh private verification key |

While a handover is pending, owner-only actions stay locked for the recipient (private key, new versions, silent-share links, workspace proofs, provenance records, and outgoing transfers).

Confirming a transfer rotates the private ownership credential: a fresh commitment secret and blinding are generated, the earlier commitment stays in the append-only `commitments` history, and the rotation is written to the ledger as `ownership_credential_rotated`. The previous owner can no longer produce a valid ownership proof for the record, and the new owner reveals the replacement key from the registration page. The chain of ownership for every record is available at `GET /api/registrations/{identifier}/ownership-chain` and in the **Ownership chain** card of the record page.

### Add organization members

An organization admin or owner opens **Organization** in the sidebar (or **Settings → Organization**) and uses **Create invitation**. The invitation works like a team invite: the admin gets a shareable code (`/join?code=...`), the invited person signs in and accepts it, and only then do the membership and the shared workspace access become active. Every organization member can open the organization's registrations and their encrypted originals.

The **Register creation** page has a **Register to organization** switch. With it on, the new creation is owned by the organization and appears on the organization page for every member; with it off the record stays personal.

The site-wide console lives at `/admin` and is restricted to the `site_admin` role. It controls accounts (role, suspension, organization assignment), disputes, organizations, teams, registrations, and the audit trail. Seed a site administrator with `python -m app.seed`, which creates `admin@authentiq.dev` with the password `Authentiq!Admin2026`.

Settings → Organization also keeps the direct provisioning flow: **Add a member** creates a real account immediately, generates a 16-character password that satisfies the strength policy, and shows it once. Share that email and password with the person over a secure channel; they sign in at `/login` and land inside the same organization.

The password is stored only as an Argon2id hash, so it cannot be displayed again. Use **New password** next to a member to issue a fresh one-time password; rotation also revokes every active session for that member. The organization owner's password cannot be reset by another admin. Email delivery is not configured in this release, so no message is sent automatically.

Legacy `org_admin` accounts without an organization receive a personal organization the first time they open the organization settings, which keeps the provisioning form available.

## Tests and builds

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers authentication and refresh rotation, password reset, organization member provisioning and password rotation, upload integrity and chunk rejection, registration authorization and duplicate detection, ZKP validity/tampering/expiry/replay, ledger and audit tampering, team allocation, transfer lifecycle, dispute lifecycle, role authorization, and dashboard aggregation.

Frontend:

```powershell
cd frontend
npm run build
```

The build runs TypeScript checking and a Vite production build.

Optional chain and circuit packages have their own test and build commands in their READMEs. They are not required for the application to run.

## Docker Compose

The stack connects to an external PostgreSQL database (Neon by default). Put the connection string, the secret key, and the rest of the settings in `.env`, then start:

```powershell
docker compose up --build
```

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Database: external PostgreSQL from `AUTHENTIQ_DATABASE_URL` (Neon)

The stack uses the external database, a named volume for encrypted files and the ledger, and an Nginx reverse proxy for `/api`. Tables are created from SQLAlchemy metadata on startup.

Create the demo login accounts inside the running stack:

```powershell
docker compose exec backend python -m app.seed
```

For a production-like environment, set `AUTHENTIQ_ENVIRONMENT=production`, `AUTHENTIQ_DEBUG=false`, a strong `AUTHENTIQ_SECRET_KEY`, restrictive CORS origins, TLS at the proxy, and email delivery. Password reset currently returns a development token instead of sending email. Team invitations always return a one-time invite code and join link in the response, because the invited person needs a way to redeem the seat without an email provider.

## Optional Polygon Amoy ledger

By default `AUTHENTIQ_LEDGER_MODE=simulation`. The local ledger is append-only and hash-chained, but it is not a blockchain and is never described as one in the UI.

To use real Polygon Amoy testnet transactions:

1. Deploy `blockchain/contracts/AuthentiqRegistry.sol` with Hardhat.
2. Authorize the backend signing address as a writer if it differs from the deployer.
3. Install `web3` and `eth-account` in the backend environment.
4. Set `AUTHENTIQ_LEDGER_MODE=polygon`, `AUTHENTIQ_CHAIN_RPC_URL`, `AUTHENTIQ_CHAIN_PRIVATE_KEY`, `AUTHENTIQ_CHAIN_CONTRACT_ADDRESS`, and `AUTHENTIQ_CHAIN_ID=80002`.
5. Restart the API and confirm `GET /api/ledger/status`.

See [blockchain/README.md](blockchain/README.md). Amoy is a public testnet; these are real testnet transactions, not mainnet settlement.

## Optional Circom circuit

`circuits/ownership.circom` proves `commitment = Poseidon(fingerprint mod p, secret)` and is useful as a reference for a future Groth16 integration. It is **not wired into the running application**. The default Schnorr proof remains the runtime proof system.

See [circuits/README.md](circuits/README.md).

## Configuration

Settings are loaded from the root `.env` or `backend/.env` with the `AUTHENTIQ_` prefix. The complete template is [.env.example](.env.example).

Frequently changed values:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AUTHENTIQ_SECRET_KEY` | JWT signing and secret encryption derivation | Development placeholder; must be replaced |
| `AUTHENTIQ_DATABASE_URL` | SQLAlchemy database URL | SQLite at `backend/authentiq.db` |
| `AUTHENTIQ_STORAGE_DIR` | Storage root | `storage/` |
| `AUTHENTIQ_LEDGER_MODE` | `simulation` or `polygon` | `simulation` |
| `AUTHENTIQ_CHAIN_*` | Polygon RPC, key, contract, chain ID | Empty / Amoy defaults |
| `AUTHENTIQ_ZKP_CHALLENGE_MINUTES` | Challenge lifetime | `10` |
| `AUTHENTIQ_ZKP_VERIFICATION_HOURS` | Verification link lifetime bound | `72` |
| `AUTHENTIQ_MAX_FILE_SIZE_MB` | Upload limit | `200` |
| `AUTHENTIQ_MAX_CHUNK_SIZE_MB` | Chunk limit | `8` |
| `AUTHENTIQ_CORS_ORIGINS` | Comma-separated allowed origins | Local Vite origins |
| `AUTHENTIQ_PUBLIC_APP_URL` | Public verification link base | `http://localhost:5173` |
| `AUTHENTIQ_SEED_DEMO` | Create demo login accounts at startup | `false` |

## API

All application endpoints are under `/api`. The browser uses bearer access tokens and rotates refresh tokens through `/api/auth/refresh`.

- OpenAPI UI: `/api/docs`
- Health: `GET /api/health`
- Full endpoint reference: [docs/API.md](docs/API.md)

## Security model

Implemented controls include Argon2id password hashing, short-lived access tokens, hashed refresh tokens, session revocation, login lockout, rate limiting, backend authorization checks, encrypted file storage, encrypted idea content, upload integrity checks, append-only audit chaining, and explicit proof freshness controls.

There is no MFA, passkey support, email delivery, hardware-backed key custody, or production key-management integration in this release. Those gaps are reported honestly in `/api/settings/security` rather than simulated. See [docs/SECURITY.md](docs/SECURITY.md).

## Known limitations

- The default ledger is a local simulation. It detects local tampering but is not distributed consensus and can be rewritten by an operator with filesystem access.
- The default ZK proof proves knowledge of the commitment opening. File-hash equality is checked separately before proving and during verification; it is not constrained inside the default circuit.
- Image similarity and AI-content classification are only enabled when real provider credentials are configured. The UI does not invent analysis results.
- Email delivery is unconfigured. Password reset and team invitation tokens are returned in development responses.
- The optional Groth16 circuit is not integrated into runtime proof generation or verification.
- There are no background workers. Certificate generation, hashing, and encryption are synchronous request work.
- There is no production migration history yet; tables are created from SQLAlchemy metadata at startup.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Technology stack](docs/TECH_STACK.md)
- [API reference](docs/API.md)
- [Security model](docs/SECURITY.md)
- [Zero-knowledge proofs](docs/ZKP.md)
- [Blockchain registry](blockchain/README.md)
- [Circom circuit](circuits/README.md)

## License

No license file is included. Add an explicit license before distributing or accepting external contributions.
