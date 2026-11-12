# AUTHENTIQ API reference

Base URL: `http://localhost:8000/api`

Interactive OpenAPI documentation: `http://localhost:8000/api/docs`

ReDoc: `http://localhost:8000/api/redoc`

OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## 1. Conventions

### Content types

- JSON requests use `Content-Type: application/json`.
- Chunk and evidence uploads use `multipart/form-data`.
- File downloads are binary streams.
- Certificates are `application/pdf`.

### Authentication

Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

Access tokens are short-lived JWTs. Refresh tokens are opaque, stored hashed on the server, rotated on every refresh, and bound to a session. Send the current refresh token to `POST /auth/refresh`. Reusing an old refresh token fails because the stored hash has changed.

### Error format

Application errors use:

```json
{
  "detail": "Human-readable message or structured validation information"
}
```

Common status codes:

| Status | Meaning |
| --- | --- |
| `400` | Invalid state or bad request |
| `401` | Missing, expired, or invalid token |
| `403` | Authenticated but not authorized |
| `404` | Resource not found or hidden by access control |
| `409` | State conflict, duplicate, replay, or usage limit |
| `410` | Expired or revoked resource |
| `413` | File or chunk too large |
| `415` | Unsupported file extension |
| `422` | Validation failure or integrity mismatch |
| `423` | Account temporarily locked |
| `429` | Rate limit exceeded; inspect `Retry-After` |
| `500` | Unexpected server error |

CORS exposes `Content-Disposition` and `Retry-After`.

### Pagination

Paginated endpoints generally accept `page` and `page_size`. Responses may include `items`, `total`, `page`, `page_size`, and `pages`. Some endpoints return a simpler shape; the tables below note the resource structure.

### Identifiers

Registration endpoints accept either the internal UUID or the public registration ID such as `AUTH-2026-...`. Ideas accept the internal UUID or `idea_ref`. Disputes accept the internal UUID or `dispute_ref`.

### Time

Timestamps are ISO 8601 strings in UTC.

## 2. System

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | No | App status, ledger mode, ZKP scheme, version |
| `GET` | `/docs` | No | Swagger UI |
| `GET` | `/redoc` | No | ReDoc |
| `GET` | `/openapi.json` | No | OpenAPI document |

Health example:

```json
{
  "status": "ok",
  "app": "AUTHENTIQ",
  "environment": "development",
  "ledger": {
    "mode": "simulation",
    "label": "Simulation Mode",
    "connected": true,
    "tamper_detected": false
  },
  "zkp": {
    "scheme": "AUTHENTIQ-SCHNORR-BN254-G1-V1",
    "poseidon": "BN254 Poseidon-254 (circomlib-compatible)"
  },
  "version": "1.0.0"
}
```

## 3. Authentication and accounts

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | No | Create an individual or organization account |
| `POST` | `/auth/login` | No | Sign in and create a session |
| `POST` | `/auth/refresh` | No | Rotate a refresh token and issue a new access token |
| `POST` | `/auth/logout` | Yes | Revoke one session or all sessions |
| `GET` | `/auth/me` | Yes | Current user profile |
| `PATCH` | `/auth/me` | Yes | Update display name or avatar color |
| `POST` | `/auth/forgot-password` | No | Create a password reset token |
| `POST` | `/auth/reset-password` | No | Consume a reset token and set a new password |
| `POST` | `/auth/change-password` | Yes | Change password and revoke all sessions |
| `GET` | `/auth/sessions` | Yes | List active sessions |
| `DELETE` | `/auth/sessions/{session_id}` | Yes | Revoke a session |

### Register

```http
POST /api/auth/register
```

```json
{
  "email": "creator@example.com",
  "password": "A-strong-password-2026",
  "display_name": "Alex Rivera",
  "account_type": "individual",
  "organization_name": null
}
```

`account_type` is `individual` or `organization`. Organization registration also accepts `organization_name` and creates an organization with an `org_admin` role.

Response `201`:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "opaque-token",
  "expires_in": 2700,
  "user": {
    "id": "uuid",
    "email": "creator@example.com",
    "display_name": "Alex Rivera",
    "account_type": "individual",
    "role": "creator",
    "organization_id": null,
    "organization_name": null,
    "avatar_color": "#3B82F6",
    "is_demo": false
  }
}
```

### Login

```json
{
  "email": "creator@example.com",
  "password": "A-strong-password-2026",
  "remember_me": false
}
```

The login rate limit is keyed by IP and email. Repeated failures lock the account temporarily after six failed attempts.

### Refresh

```json
{
  "refresh_token": "opaque-token"
}
```

The response is a new token pair. The previous refresh token is invalidated.

### Logout

```json
{
  "refresh_token": "opaque-token"
}
```

If `refresh_token` is omitted, all active sessions for the user are revoked.

### Forgot and reset password

```json
{
  "email": "creator@example.com"
}
```

Outside production, the response includes a `detail` field containing the development reset token. No email is sent. Use the token with `/auth/reset-password`:

```json
{
  "token": "reset-token",
  "new_password": "A-new-strong-password-2026"
}
```

### Change password

```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

A successful password change revokes every active session. The frontend signs the user out.

## 4. Uploads and fingerprints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/uploads/initiate` | Yes | Start a chunked upload |
| `POST` | `/uploads/{upload_id}/chunk` | Yes | Upload and verify one chunk |
| `POST` | `/uploads/{upload_id}/complete` | Yes | Assemble, scan, hash, and encrypt |
| `GET` | `/uploads/{upload_id}` | Yes | Upload status |
| `POST` | `/fingerprints/generate` | Yes | Compute SHA-256 over a supplied file |
| `POST` | `/fingerprints/verify` | Yes | Compare a SHA-256 and a fingerprint |

### Initiate

```json
{
  "filename": "brand-system.png",
  "size_bytes": 1048576,
  "mime_type": "image/png",
  "total_chunks": 2,
  "chunk_size": 524288,
  "client_sha256": "64-hex-character-digest"
}
```

`total_chunks` must equal `ceil(size_bytes / chunk_size)`. The extension must be on the server allow-list. The default maximum file size is 200 MB and the maximum chunk size is 8 MB.

Response:

```json
{
  "upload_id": "uuid",
  "filename": "brand-system.png",
  "size_bytes": 1048576,
  "total_chunks": 2,
  "chunk_size": 524288,
  "uploaded_chunks": 0,
  "status": "initiated",
  "final_sha256": null
}
```

### Upload chunk

```http
POST /api/uploads/{upload_id}/chunk
Content-Type: multipart/form-data
```

Fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `chunk_index` | integer | Zero-based chunk index |
| `sha256` | string | SHA-256 of this chunk |
| `file` | binary | Raw chunk bytes |

Non-final chunks must be exactly the declared chunk size. A mismatched hash is rejected with `422`.

### Complete

```http
POST /api/uploads/{upload_id}/complete
Content-Type: multipart/form-data
```

Optional field `client_sha256` must match the assembled file. Completion verifies every chunk, rejects missing or corrupted chunks, runs the scanner gate, encrypts the final file with AES-256-GCM, deletes temporary chunks, and stores the final SHA-256.

The upload must reach `status=completed` before registration.

## 5. Registrations

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/registrations` | Yes | Create a registration from a completed upload |
| `POST` | `/registrations/duplicate-check` | Yes | Check a fingerprint against existing registrations before uploading |
| `GET` | `/registrations` | Yes | List accessible registrations |
| `GET` | `/registrations/{identifier}` | Yes | Registration detail |
| `GET` | `/registrations/{identifier}/file` | Yes | Decrypt and download the original file |
| `GET` | `/registrations/{identifier}/certificate` | Yes | Download a PDF certificate |
| `GET` | `/registrations/{identifier}/trust-score` | Yes | Explainable ownership evidence score |
| `GET` | `/registrations/{identifier}/evidence-packet` | Yes | Download the ZIP evidence packet |
| `GET` | `/registrations/{identifier}/verification-state` | Yes | Ledger record and recent proofs |

### Create

```json
{
  "upload_id": "uuid",
  "title": "Aurora Identity System",
  "description": "Visual identity system for the Aurora product line.",
  "asset_type": "image",
  "creation_timestamp": "2026-10-01T12:00:00Z",
  "privacy": "public_fingerprint",
  "tags": ["brand", "identity"]
}
```

Allowed asset types: `image`, `document`, `pdf`, `source_code`, `design`, `research`, `audio`, `video`, `ai_generated`, `other`.

Allowed privacy modes: `private`, `public_fingerprint`, `public`.

Response includes:

```json
{
  "registration": {
    "registration_id": "AUTH-2026-...",
    "title": "Aurora Identity System",
    "sha256": "64-hex",
    "commitment": "0x...",
    "ledger_tx_id": "aqtx_...",
    "ledger_mode": "simulation",
    "status": "registered"
  },
  "alerts_created": 0,
  "duplicates": {
    "exact_matches": [],
    "similar_matches": [],
    "checked": true,
    "explanation": "Exact matches share an identical SHA-256 fingerprint. Similar matches use a dHash-64 perceptual comparison of the image."
  },
  "ledger": {
    "mode": "simulation",
    "tx_id": "aqtx_...",
    "simulated": true
  },
  "certificate_url": "/api/registrations/{id}/certificate"
}
```

### Duplicate check

`POST /api/registrations/duplicate-check` answers the question "is this document already registered?" before any bytes are uploaded. The browser hashes the file locally and sends the digest, optionally with a perceptual hash computed from a canvas for images.

```json
{
  "sha256": "64-hex",
  "perceptual_hash": "16-hex"
}
```

`perceptual_hash` is optional and is only produced for images. It uses the same dHash-64 comparison the server uses on stored files, so a re-encoded image is still matched.

Response:

```json
{
  "exact_matches": [
    {
      "registration_id": "AQ-2026-50C58A40",
      "id": "uuid",
      "title": "Original Document",
      "file_name": "document.pdf",
      "asset_type": "document",
      "registered_at": "2026-11-11T14:25:43.406485",
      "similarity": 1.0,
      "method": "exact_sha256",
      "owned_by_you": false,
      "same_organization": false
    }
  ],
  "similar_matches": [],
  "checked": true,
  "explanation": "Exact matches share an identical SHA-256 fingerprint. Similar matches use a dHash-64 perceptual comparison of the image."
}
```

Exact matches share an identical SHA-256 fingerprint. Similar matches score 0.90 or higher on the dHash-64 perceptual comparison. The response deliberately does not name the other account; the duplicate alert and notification workflow is what discloses the other party, and only to the owner of the existing record.

### List query parameters

`page`, `page_size`, `q`, `asset_type`, `status`, `sort` (`recent`, `oldest`, `title`).

The list is scoped to the user and, for organization members, the user's organization.

## 6. Versions

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/versions` | Yes | Add a version from a completed upload |
| `GET` | `/versions/registration/{registration_id}` | Yes | List versions for a registration |
| `GET` | `/versions/compare` | Yes | Compare two versions |
| `GET` | `/versions/{version_id}` | Yes | Version detail |
| `GET` | `/versions/{version_id}/file` | Yes | Download version file |
| `GET` | `/versions/{version_id}/certificate` | Yes | Download version certificate |

Create:

```json
{
  "registration_id": "AUTH-2026-...",
  "upload_id": "uuid",
  "change_description": "Refined the mark and tightened icon geometry."
}
```

Comparison accepts `left` and `right` version IDs and reports whether the files and metadata differ.

## 7. Zero-knowledge proofs

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/zkp/challenge` | Yes | Create a fresh nonce |
| `POST` | `/zkp/generate` | Yes | Generate a proof from a file fingerprint |
| `POST` | `/zkp/verify` | Yes | Verify a proof |
| `GET` | `/zkp/proofs/{registration_id}` | Yes | List recent proofs |

### Challenge

```json
{
  "registration_id": "AUTH-2026-...",
  "purpose": "proof"
}
```

Purposes: `proof`, `share`, `anonymous`.

Response:

```json
{
  "challenge_id": "uuid",
  "nonce": "random-nonce",
  "expires_at": "2026-11-11T12:10:00Z",
  "registration_id": "AUTH-2026-...",
  "fingerprint": "64-hex",
  "commitment": "0x...",
  "poseidon_commitment": "0x...",
  "proof_system": "AUTHENTIQ-SCHNORR-BN254-G1-V1",
  "statement": "...",
  "is_groth16": false
}
```

### Generate

```json
{
  "registration_id": "AUTH-2026-...",
  "challenge_id": "uuid",
  "file_sha256": "64-hex"
}
```

The supplied hash must equal the registered fingerprint. The server decrypts the witness, creates a non-interactive Schnorr proof, marks the challenge used, stores the proof, writes an audit event, and returns the proof package.

### Verify

```json
{
  "registration_id": "AUTH-2026-...",
  "nonce": "random-nonce",
  "proof": {},
  "public_signals": {}
}
```

A successful verification marks the proof and registration as verified and records a ledger event. A challenge can only produce one successful verification.

## 8. Silent sharing and public verification

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/sharing/create` | Yes | Create a verification link and proof package |
| `GET` | `/sharing` | Yes | List links created by the user |
| `DELETE` | `/sharing/{verification_id}` | Yes | Revoke a link |
| `GET` | `/public/verify/{verification_id}` | No | Public disclosure-limited metadata |
| `POST` | `/public/verify/{verification_id}` | No | Verify a proof package |
| `GET` | `/public/records` | No | Public records registry: search and page records whose owner chose the Public disclosure level |

The public records registry lists only registrations with `privacy` of `public`. Private records and fingerprint-only records are never enumerated there; they stay reachable only through their reference or a silent-sharing link. It accepts `q`, `asset_type`, `sort`, `page`, and `page_size`, and truncates descriptions to a preview length.

### Create

```json
{
  "registration_id": "AUTH-2026-...",
  "expires_in_hours": 72,
  "max_uses": 1,
  "message": "Please verify this ownership record.",
  "disclosure": {
    "show_reference": true,
    "show_registration_date": true,
    "show_fingerprint": false,
    "show_organization": false,
    "anonymous": true
  }
}
```

Response:

```json
{
  "verification_id": "vrf_...",
  "verification_url": "http://localhost:5173/verify/vrf_...",
  "expires_at": "2026-11-14T12:00:00Z",
  "max_uses": 1,
  "disclosure": {},
  "proof_system": "AUTHENTIQ-SCHNORR-BN254-G1-V1",
  "proof_package": {
    "format": "AUTHENTIQ-VERIFICATION-PACKAGE-V1",
    "verification_id": "vrf_...",
    "registration_reference": "AUTH-2026-...",
    "nonce": "random-nonce",
    "proof": {},
    "public_signals": {},
    "disclosure": {},
    "issued_at": "2026-11-11T12:00:00Z"
  }
}
```

### Public verify

```json
{
  "proof_package": {}
}
```

The endpoint also accepts `proof` and `public_signals` directly. It enforces:

- The link exists, is not revoked, and is not expired.
- The usage count is below `max_uses`.
- The proof's registration reference matches.
- The proof's fingerprint matches the stored registration.
- The nonce matches the one-time challenge.
- The Schnorr equation and Fiat-Shamir challenge are valid.
- The disclosure policy limits returned metadata.

Public responses never include the original file, private witness, password, or personal identity.

### Anonymous ownership verification (no login)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/registrations/{identifier}/verification-key` | Yes | Re-issue the creator's private verification key |
| `GET` | `/registrations/{identifier}/ownership-chain` | Yes | Append-only chain of ownership for a record |
| `POST` | `/public/verify/anonymous/challenge` | No | Check the file fingerprint and issue a single-use challenge |
| `POST` | `/public/verify/anonymous/verify` | No | Verify a browser-generated Schnorr proof |
| `POST` | `/public/fingerprints/check` | No | Public existence check for a SHA-256 fingerprint |

Request a challenge:

```json
{
  "registration_id": "AQ-2026-1A2B3C4D",
  "file_sha256": "64 lowercase hex characters"
}
```

Response:

```json
{
  "challenge_id": "uuid",
  "nonce": "one-time nonce",
  "expires_at": "2026-11-11T12:10:00Z",
  "registration_id": "AQ-2026-1A2B3C4D",
  "fingerprint": "sha256",
  "commitment": "0x...",
  "proof_system": "AUTHENTIQ-SCHNORR-BN254-G1-V1",
  "statement": "...",
  "challenge_minutes": 10
}
```

The browser then builds the proof locally from the private verification key (`aqv1_<opening>_<blinding>`) and submits:

```json
{
  "challenge_id": "uuid",
  "proof": {
    "scheme": "AUTHENTIQ-SCHNORR-BN254-G1-V1",
    "commitment": "0x...",
    "anchor": "0x...",
    "challenge": "0x...",
    "response": ["64 hex characters", "64 hex characters"],
    "public_signals": {}
  }
}
```

The response includes `valid`, `message`, the public record, and `checks` with `registration_exists`, `file_fingerprint_matches`, `challenge_valid`, `proof_valid`, `private_key_disclosed` (`false`), and `login_required` (`false`). The private key is never transmitted: only the proof is.

## 9. Ideas

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/ideas` | Yes | Protect an idea with a Poseidon commitment |
| `GET` | `/ideas` | Yes | List the user's ideas |
| `GET` | `/ideas/{identifier}` | Yes | Idea detail |
| `POST` | `/ideas/{identifier}/revisions` | Yes | Add an encrypted revision |
| `PATCH` | `/ideas/{identifier}/notes` | Yes | Update encrypted notes |
| `POST` | `/ideas/{identifier}/reveal` | Yes | Reveal the idea and record the reveal |
| `GET` | `/ideas/{identifier}/certificate` | Yes | Download idea certificate |
| `GET` | `/ideas/{identifier}/evidence` | Yes | Download evidence package |

Create:

```json
{
  "title": "Adaptive trust-scoring mesh",
  "description": "A decentralized trust graph that adjusts verification requirements...",
  "privacy": "private"
}
```

Privacy: `private`, `timestamp_only`, `organization`.

The commitment is `Poseidon(SHA256(title + newline + description), secret)`. The description and secret are encrypted at rest.

## 10. Provenance

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/provenance/analyze` | Yes | Run configured similarity/AI analysis |
| `POST` | `/provenance/record` | Yes | Record an AI/human provenance declaration |
| `GET` | `/provenance` | Yes | List provenance records |
| `GET` | `/provenance/{registration_id}` | Yes | Detail for a registration |

Record example:

```json
{
  "registration_id": "AUTH-2026-...",
  "declared_ai": true,
  "model_name": "Example Model",
  "tool_name": "Example Tool",
  "prompt_commitment": "0x...",
  "human_contribution": "Concept and final editing by the creator.",
  "editing_details": "Color grading and export handled in-house.",
  "creation_date": "2026-10-01T12:00:00Z"
}
```

If no real classifier or similarity provider is configured, analysis reports `analysis_available: false` with a reason. It does not fabricate a score.

## 11. Teams

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/teams` | Yes | Create a team project |
| `GET` | `/teams` | Yes | List owned or joined projects, including pending invitations addressed to your email |
| `GET` | `/teams/{project_id}` | Yes | Project detail; pass `?invite={token}` to open a project you hold a code for |
| `POST` | `/teams/{project_id}/invite` | Manager | Invite by email; returns a one-time invite code and join link |
| `POST` | `/teams/{project_id}/join` | Yes | Accept an invitation addressed to your email |
| `POST` | `/teams/redeem` | Yes | Redeem an invite code and join the project that issued it |
| `POST` | `/teams/{project_id}/contributions` | Member | Submit a contribution |
| `PATCH` | `/teams/{project_id}/contributions/{contribution_id}/approve` | Manager | Approve a contribution |
| `POST` | `/teams/{project_id}/ownership/propose` | Manager | Propose percentages |
| `POST` | `/teams/{project_id}/ownership/approve` | Member | Approve proposed allocations |
| `GET` | `/teams/{project_id}/ownership` | Member | Allocation state |
| `GET` | `/teams/{project_id}/certificate` | Member | Team ownership certificate |

Create:

```json
{
  "name": "Aurora Launch Consortium",
  "description": "Joint ownership project covering the Aurora identity launch."
}
```

Invite:

```json
{
  "email": "collaborator@example.com",
  "role": "contributor",
  "display_name": "Maya Chen"
}
```

Roles: `contributor`, `reviewer`, `co_owner`. The invite response always includes a one-time `invite_token` and a `invite_url` of the form `/teams/{project_id}?invite={token}`. Email delivery is not configured, so the owner shares the token or the link directly.

There are two ways for the invited person to join:

1. **Pending invitation.** If the invited email already has an account, that account sees the project in `GET /teams` with `my_status` of `invited` and can press Accept invitation, which calls `POST /teams/{project_id}/join` with an empty body.
2. **Invite code.** The invited person signs in, opens the Teams page, and pastes the code into "Join with an invitation code". That calls `POST /teams/redeem` with the token:

```json
{ "token": "AR2iEOSp4nUQkn232EPHq13UhkZt0E9h" }
```

Redeeming activates the membership with the role the owner assigned and returns the project id and name. A code is single-use: the token is cleared once redeemed. If the code was issued to an email that already belongs to another account, the redeem is refused and the invited address is reported instead.

Opening `/teams/{project_id}?invite={token}` with a valid code lets a signed-in user view the project and press Accept invitation without pasting the code into the form.

Propose allocations:

```json
{
  "allocations": [
    { "member_id": "uuid-1", "percent": 70 },
    { "member_id": "uuid-2", "percent": 30 }
  ]
}
```

The backend requires the total to equal 100% and requires every active member to approve before the allocation is finalized.

## 12. Organizations

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/settings/organization` | Yes | Organization, members, open invitations, registration count |
| `POST` | `/settings/organization` | Yes | Create an organization for the signed-in account |
| `POST` | `/settings/organization/invitations` | Org admin | Issue an invitation code |
| `GET` | `/settings/organization/invitations` | Yes | List invitations |
| `DELETE` | `/settings/organization/invitations/{invitation_id}` | Org admin | Revoke an invitation |
| `POST` | `/settings/organization/invitations/accept` | Yes | Redeem an invitation and join |
| `GET` | `/settings/organization/registrations` | Yes | Every creation owned by the organization |
| `POST` | `/settings/organization/members` | Org admin | Provision a member account with a generated one-time password |
| `POST` | `/settings/organization/members/{member_id}/password` | Org admin | Rotate a member password and revoke that member's sessions |
| `PATCH` | `/settings/organization` | Org admin | Rename the organization |
| `POST` | `/registrations` | Yes | `scope_to_organization` decides if the record is organization owned |

Two ways to add a person to an organization:

1. **Invitation code.** The admin issues an invitation, shares the code or the `/join?code=...` link, and the recipient redeems it. Accepting sets the account's `organization_id`, activates the membership with the invited role, and grants access to the organization's registrations and their encrypted originals. Codes are single-use and expire.
2. **Direct provisioning.** The admin creates the account outright. The backend generates a sixteen-character password, stores only its Argon2id hash, and returns the plaintext once in `credentials.password`. Rotation issues a new one-time password and revokes the member's sessions. Provisioning is limited to thirty accounts per administrator per hour.

Issue an invitation:

```json
{ "email": "teammate@company.com", "display_name": "Teammate", "role": "org_member" }
```

The response contains `invitation.invite_token` and `invitation.invite_url` (`/join?code=...`). The invited account redeems it:

```json
{ "token": "AR2iEOSp4nUQkn232EPHq13UhkZt0E9h" }
```

Provision a member directly:

```json
{ "display_name": "Teammate", "email": "teammate@company.com", "role": "org_member" }
```

The response returns `credentials.email` and `credentials.password`. The password is shown once and cannot be recovered; rotate it with the member password endpoint if it is lost.

`POST /registrations` accepts `scope_to_organization`:

- `true` - the creation is owned by the organization and visible to every member.
- `false` - the creation stays on the personal account only.
- omitted - automatic behaviour (organization accounts register under the organization).

## 13. Transfers

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/transfers` | Owner | Propose a transfer |
| `GET` | `/transfers` | Yes | List incoming/outgoing transfers |
| `GET` | `/transfers/history/{registration_id}` | Yes | Append-only transfer history |
| `POST` | `/transfers/{transfer_id}/accept` | Recipient | Accept |
| `POST` | `/transfers/{transfer_id}/reject` | Recipient | Reject |
| `POST` | `/transfers/{transfer_id}/cancel` | Owner | Cancel |
| `POST` | `/transfers/{transfer_id}/confirm` | Owner | Finalize after acceptance |

Create:

```json
{
  "registration_id": "AUTH-2026-...",
  "recipient_email": "recipient@example.com",
  "to_organization_id": null,
  "reason": "Handing stewardship to the implementation lead."
}
```

The recipient must already have an account. Recipient acceptance moves the transfer to `recipient_accepted`; owner confirmation moves it to `completed` and changes the registration owner.

### Ownership handover behaviour

| Stage | Recorded owner | Recipient access | Owner-only actions |
| --- | --- | --- | --- |
| `pending_recipient` | Current owner | Read access to the record, the encrypted original, metadata, and proofs | Owner only |
| `recipient_accepted` | Current owner | Same read access, shown as *incoming ownership* in the workspace | Owner only |
| `completed` | Recipient | Full access: file, metadata, versions, proofs, certificate, evidence packet, private verification key | Recipient |

- `GET /api/registrations` and `GET /api/dashboard/summary` include records whose ownership is being handed to the signed-in user. Each item carries `ownership_status` (`owned` or `pending_confirmation`) and `pending_ownership`.
- `GET /api/registrations/{identifier}` returns an `ownership` block and a `file` block with the stored file metadata (original name, MIME type, extension, size, encrypted size, chunks, perceptual hash, extracted text).
- `GET /api/registrations/{identifier}/ownership-chain` returns the append-only chain: the registration event plus every transfer with names, reasons, timestamps, and ledger transaction ids.
- Owner-only endpoints (`/registrations/{id}/verification-key`, `POST /versions`, `POST /sharing/create`, `POST /zkp/challenge`, `POST /zkp/generate`, `POST /provenance/record`) return `403` while a handover is pending.
- Completing a transfer **rotates the private ownership credential**: a new commitment secret and blinding are generated, the previous commitment is kept in the `commitments` table, and the rotation is written to the ledger as `ownership_credential_rotated`. The previous owner's verification key stops proving ownership; the new owner reveals the new key from the record.

Reject body:

```json
{
  "reason": "Optional rejection reason"
}
```

List query parameters: `page`, `page_size`, `status`, `direction` (`all`, `outgoing`, `incoming`).

## 14. Disputes

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/disputes` | Yes | Open a dispute |
| `GET` | `/disputes` | Yes | List visible disputes |
| `GET` | `/disputes/{dispute_id}` | Party/reviewer | Dispute detail |
| `POST` | `/disputes/{dispute_id}/evidence` | Party/reviewer | Upload encrypted evidence |
| `GET` | `/disputes/{dispute_id}/evidence/{evidence_id}` | Party/reviewer | Download evidence |
| `POST` | `/disputes/{dispute_id}/status` | Party/reviewer | Update status or resolve |
| `GET` | `/disputes/{dispute_id}/report` | Party/reviewer | Generate evidence report JSON |

Create:

```json
{
  "registration_id": "AUTH-2026-...",
  "reason": "Conflicting prior-use claim",
  "description": "A conflicting claim was submitted with prior correspondence attached."
}
```

Status update:

```json
{
  "status": "under_review",
  "resolution": "Optional unless resolving or rejecting"
}
```

Allowed statuses: `under_review`, `evidence_requested`, `resolved`, `rejected`.

Only a verifier or an organization admin in the registration's organization can set `resolved` or `rejected`, and those transitions require a resolution summary. A verifier sees all disputes; other users see disputes where they are the claimant or respondent.

The report includes related registrations with the same fingerprint, earliest-registration priority evidence, ledger audit, proof verification summary, versions, transfers, evidence, audit trail, and a limitations statement.

## 15. Alerts

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/alerts` | Yes | List ownership alerts |
| `GET` | `/alerts/{alert_id}` | Yes | Alert detail with similarity data |
| `PATCH` | `/alerts/{alert_id}/status` | Yes | Update investigation state |

List query parameters: `page`, `page_size`, `status`, `alert_type`.

Status update:

```json
{
  "status": "under_review",
  "investigation_notes": "Reviewing the matched registration."
}
```

Allowed statuses: `under_review`, `resolved`, `dismissed`.

## 16. Ledger

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/ledger/status` | Yes | Adapter mode, connectivity, block count, tamper state |
| `GET` | `/ledger/transactions` | Yes | Recent transactions |
| `GET` | `/ledger/transactions/{tx_id}` | Yes | Transaction detail |
| `POST` | `/ledger/audit` | Yes | Verify the active ledger |

Simulation status includes the explicit message that no public blockchain transaction is created. Polygon status reports the configured chain ID, contract address, latest block, and connection state.

### 15.1 Integrity center

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/integrity/overview` | Yes | Recompute ledger chain, audit chain, storage presence, ledger linkage, duplicate fingerprints, workspace digest, and exposure counts |

The response is assembled from live data on every call. `workspace_digest` is the SHA-256 of a canonical snapshot of the caller's registrations, so two identical workspaces produce the same digest and any change produces a new one. `checks.missing_files` and `checks.missing_ledger_records` list references that could not be resolved. No value is estimated or seeded.

### 15.2 Trust score

`GET /api/registrations/{identifier}/trust-score` returns an explainable evidence score for one record.

| Factor | Maximum | Basis |
| --- | --- | --- |
| `fingerprint` | 25 | SHA-256 fingerprint plus a Poseidon commitment |
| `ledger` | 25 | Ledger block re-read and hash-verified |
| `proofs` | 20 | 10 points per verified zero-knowledge proof, capped |
| `file_integrity` | 15 | Stored file decrypted and re-hashed against the registered SHA-256 |
| `visual_signature` | 5 | dHash-64 perceptual signature present |
| `duplicates` | penalty | 5 points per duplicate indicator, capped at 15 |
| `disputes` | penalty | 10 points per open dispute, capped at 20 |

Scores are clamped to 0–100 and graded as `verified` (90+), `strong` (70+), `developing` (45+), or `unverified`. The score is an evidence indicator, not a legal finding.

### 15.3 Evidence packet

`GET /api/registrations/{identifier}/evidence-packet` streams a ZIP:

| Entry | Contents |
| --- | --- |
| `manifest.json` | Canonical manifest with registration, file metadata, ledger record, proofs, trust factors, verification URL, and `manifest_sha256` |
| `certificate.pdf` | The same PDF certificate the API serves directly |
| `ledger-receipt.json` | Ledger block number, record hash, previous hash, payload digest, and the raw record |
| `file.sha256.txt` | Fingerprint in `sha256sum` format |
| `VERIFY.txt` | Step-by-step offline verification instructions and the explicit trust boundary |

Every download writes an `evidence_packet_downloaded` audit event. The packet is a convenience export: it does not expose the decrypted original file or the commitment secret.

## 17. Notifications, audit, search, and settings

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/notifications` | Yes | Inbox with optional `unread_only` and `category` |
| `PATCH` | `/notifications/{notification_id}/read` | Yes | Mark one read |
| `POST` | `/notifications/read-all` | Yes | Mark all read |
| `DELETE` | `/notifications/{notification_id}` | Yes | Dismiss one |
| `GET` | `/audit-logs` | Yes | List audit events |
| `GET` | `/audit-logs/verify` | Yes | Verify the audit hash chain |
| `GET` | `/search?q=` | Yes | Search accessible entities |
| `GET` | `/settings/organization` | Yes | Organization, members, and whether you can manage them |
| `PATCH` | `/settings/organization` | Org admin | Rename organization |
| `POST` | `/settings/organization/members` | Org admin | Create a member account and return a one-time generated password |
| `POST` | `/settings/organization/members/{member_id}/password` | Org admin | Rotate a member password and revoke their sessions |
| `GET` | `/settings/security` | Yes | Security capabilities and honest availability flags |

Search returns matching registrations, ideas, teams, disputes, and alerts, scoped to the user's access.

An organization admin or owner can provision a real account with `POST /settings/organization/members`. The request accepts `display_name`, `email`, and a `role` of `org_member` or `org_admin`. The backend generates a 16-character password that satisfies the platform strength policy, stores only its Argon2id hash, creates an active membership immediately, and returns the plaintext password exactly once in `credentials.password`. Email delivery is not configured, so the response instructs the administrator to copy the credentials and share them over a secure channel. The generated account can sign in at `/login` and lands inside the same organization.

`POST /settings/organization/members/{member_id}/password` issues a new one-time password for an existing member, clears failed-login counters, and revokes every active session for that account. The organization owner's own password cannot be reset through this endpoint; owners rotate their password through the standard account flow instead. Member provisioning is limited to 30 creations per administrator per hour, and every creation or rotation is written to the audit log.

Legacy `org_admin` accounts that were created without an organization are given a personal organization on first access to the settings organization view, so the provisioning form is always available to administrators.

The security overview reports whether passkeys and MFA are available. In this release both are unavailable, and the response explains that they are not configured rather than pretending they are active.

## 18. Dashboard

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/dashboard/summary` | Yes | Counts, recent registrations, ledger status, proof statistics |
| `GET` | `/dashboard/activity` | Yes | Recent activity feed |

Dashboard values are computed from database records and ledger state. Static marketing statistics are not used.

## 19. Example end-to-end request sequence

```text
POST /api/auth/login
GET  /api/dashboard/summary
POST /api/uploads/initiate
POST /api/uploads/{id}/chunk          (repeated)
POST /api/uploads/{id}/complete
POST /api/registrations
GET  /api/registrations/{identifier}
POST /api/zkp/challenge
POST /api/zkp/generate
POST /api/zkp/verify
POST /api/sharing/create
GET  /api/public/verify/{verification_id}
POST /api/public/verify/{verification_id}
GET  /api/registrations/{identifier}/certificate
POST /api/ledger/audit
GET  /api/audit-logs/verify
```

## 20. Rate limits

| Operation | Limit |
| --- | --- |
| Account registration | 10 per IP per hour |
| Login | Configurable, default 8 per IP/email per 300 seconds |
| Proof generation | 40 per user per hour |
| Share creation | 30 per user per hour |
| Public verification | 30 per IP per 10 minutes |

Limits are in-process. A multi-process deployment needs a shared rate-limit store.

## 21. Site administration

Every endpoint requires the `site_admin` role and returns `403` otherwise. The console sits above the organization and workspace roles.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/admin/overview` | Deployment counters, ledger status, recent users, disputes, and audit entries |
| `GET` | `/admin/users` | Search and page through every account |
| `PATCH` | `/admin/users/{user_id}` | Change role, activate or suspend (suspension revokes every session), move accounts between organizations |
| `GET` | `/admin/disputes` | Every dispute in the deployment |
| `PATCH` | `/admin/disputes/{dispute_id}` | Change dispute status and write the resolution |
| `GET` | `/admin/organizations` | Organizations with member, registration, and invitation counts |
| `GET` | `/admin/registrations` | Every registration with its owner and organization |
| `GET` | `/admin/teams` | Team projects |
| `GET` | `/admin/audit` | The hash-chained audit trail |

Update an account:

```json
{ "role": "verifier", "is_active": false }
```

Suspending an account revokes every active session for that user. An administrator cannot suspend their own account.
