# AUTHENTIQ security model

## 1. Scope and posture

AUTHENTIQ protects creative-work records, encrypted files, ownership histories, and verification proofs. This document describes the implemented controls, the threats they address, and the residual risks that remain.

The project follows a **real behaviour over impressive claims** rule:

- Hashes, commitments, proofs, encryption, and audit chains are computed, not simulated.
- The local ledger is called a simulation, not a blockchain.
- The security settings endpoint reports MFA and passkeys as unavailable.
- AI analysis reports unavailable when no classifier is configured.
- Development password-reset tokens are returned only outside production and are labelled development behaviour.
- Team invite codes are returned to the inviting owner in every environment, because email delivery is not configured. The code is a bearer credential: whoever holds it can redeem the seat. Codes are single-use and are cleared on redemption.

## 2. Assets

| Asset | Sensitivity |
| --- | --- |
| Original creative files | High; confidential intellectual property |
| Dispute evidence | High; may contain personal or commercial information |
| Idea descriptions and notes | High; encrypted at rest |
| Commitment secrets and blinding factors | Critical; reveal the opening of ownership commitments |
| Passwords and session tokens | Critical |
| JWT signing key and file encryption key material | Critical |
| Audit and ledger history | High integrity value |
| Polygon writer private key | Critical if chain mode is enabled |
| User and organization metadata | Moderate |

## 3. Actors and trust boundaries

| Actor | Trust |
| --- | --- |
| Anonymous visitor | Untrusted; can only access public verification, the public records registry, and authentication endpoints |
| Authenticated creator | Own resources only |
| Organization member | Own resources plus the shared organization workspace |
| Organization admin | Own resources and organization-scoped resources |
| Verifier | Dispute review across the platform |
| Site administrator | Platform-wide operational read and narrow writes over users, organizations, and disputes |
| Backend process | Trusted application boundary; holds keys and decrypts files |
| Database and filesystem operator | Trusted for availability, not for tamper resistance |
| Polygon network | Public testnet; provides independent transaction inclusion when enabled |
| Email provider | Not configured in this release |

The browser is not trusted with commitment secrets, encryption keys, or authorization decisions. Every protected operation re-checks ownership or role in the backend.

## 4. Authentication controls

### Password storage

Passwords are hashed with Argon2id using:

- time cost 3
- memory cost 65,536 KiB
- parallelism 4
- 32-byte hash
- 16-byte salt

The stored hash includes algorithm parameters and salt. Verification uses constant-time comparison inside the Argon2 library. Password minimum length defaults to 10 characters and is enforced by the request schema.

### Tokens

| Token | Format | Lifetime | Storage |
| --- | --- | --- | --- |
| Access | JWT HS256 | 45 minutes by default | Browser `localStorage` |
| Refresh | Random 48-byte URL-safe token | 14 days by default; 30 days with remember-me | Hash stored in database; browser `localStorage` |
| Password reset | JWT HS256 with reset type | 30 minutes | Hash stored in database |
| Team invite | Random URL token | Project invitation lifecycle | Hash or token field in database |

Access tokens contain user ID, session ID, role, organization ID, issued-at, expiry, and JWT ID. The server validates token type and expiry. Refresh tokens rotate on every use; the previous token hash is replaced, so replay of an old refresh token fails. Logout revokes the session. Password changes and resets revoke all sessions.

### Lockout and rate limiting

- Six failed logins lock the account for 15 minutes.
- Login rate limiting is keyed by IP and email; defaults are 8 attempts per 300 seconds.
- Registration is limited to 10 attempts per IP per hour.
- Proof generation is limited to 40 per user per hour.
- Share creation is limited to 30 per user per hour.
- Public verification is limited to 30 attempts per IP per 10 minutes.

Rate limiting is in-process and resets on restart. Multi-worker deployments need Redis or another shared limiter.

### Session visibility

Users can list active sessions and revoke individual sessions. The session record stores user agent, IP address, creation time, last use, and expiry.

## 5. Authorization controls

Authorization is backend-enforced through dependencies and access helpers. It does not rely on hidden UI elements.

| Resource | Rule |
| --- | --- |
| Uploads | Owner only |
| Registrations | Owner, same organization, or public policy for public metadata; file download requires access |
| Versions | Access to the parent registration |
| Ideas | Owner only |
| Proofs | Access to the registration |
| Sharing links | Creator for management; public for disclosure-limited verification |
| Teams | Active member or owner; management by owner or co-owner |
| Transfers | Current owner creates and confirms; recipient accepts or rejects; either party can cancel |
| Disputes | Claimant, respondent, verifier, or same-organization admin |
| Dispute resolution | Verifier or same-organization admin only |
| Audit logs | Authenticated user; response is scoped in the router |
| Settings | Organization owner or admin for updates |
| Member provisioning | Organization owner or an `org_admin`; duplicate emails are rejected case-insensitively |
| Member password rotation | Organization owner or an `org_admin`; the owner's own password is excluded |
| Organization invitation code | Single-use, expiring code issued by an organization admin; redemption binds the seat to the redeeming account |
| Public records registry | Open, but lists only records whose owner chose the Public disclosure level |
| Site administration | `site_admin` role only; suspending an account revokes every one of that user's sessions |

Responses use `404` in several places where revealing existence would leak information. Public verification applies the stored disclosure policy, not the registration's full metadata.

Organization provisioning creates a real account with an independently generated 16-character password. The password mixes lowercase, uppercase, digits, and symbols, is validated against the same strength policy as public registration, and is stored only as an Argon2id hash. The plaintext is returned exactly once and is never persisted or logged. Because email delivery is not configured, the administrator is responsible for transmitting the credential over a secure channel. Password rotation clears failed-login counters and revokes every active session for the member. Every provisioning and rotation event is appended to the audit chain with the actor, target, role, and client context.

## 6. Cryptography

### File fingerprints

SHA-256 is computed over exact file bytes. Chunked uploads hash each chunk, verify each chunk on arrival, re-verify chunks before assembly, and compare the assembled digest with the client digest. The registered fingerprint is the SHA-256 of the completed file.

### Ownership commitment

```text
p  = BN254 scalar field prime
fp = SHA256(file) interpreted as an integer, reduced modulo p
s  = Poseidon(fp, secret)
C  = sG + rH
```

- `G` is the BN254 G1 generator.
- `H` is derived by hashing a fixed label to a curve point.
- `secret` and blinding factor `r` are random field elements.
- `secret` and `r` are encrypted with Fernet before database storage.

The Poseidon value is also stored as the registration commitment and displayed in the UI. The Pedersen commitment is used by the proof.

### Zero-knowledge proof

The runtime scheme is a non-interactive Schnorr proof of knowledge of `(s, r)` such that `C = sG + rH`, where `s = Poseidon(fp, secret)`. The challenge is Fiat-Shamir over the scheme identifier, anchor, commitment, fingerprint, registration ID, and nonce.

Verification checks the challenge and the group equation. Public signals bind the proof to the registration, fingerprint, and nonce. See [ZKP.md](ZKP.md).

**Scope limitation:** the default circuit does not prove that the fingerprint equals SHA-256 of a committed file. The server compares the uploaded file hash with the registered hash before generating the proof, and compares proof signals during verification. This binding is part of the protocol but outside the proof itself.

### File encryption at rest

Final uploads and evidence use `AQVL1`:

- AES-256-GCM
- 1 MiB plaintext chunks
- random 8-byte nonce prefix plus a 32-bit counter per chunk
- chunk counter bound as authenticated associated data
- 16-byte authentication tag per chunk
- versioned magic header

The key is derived as `SHA256(AUTHENTIQ_SECRET_KEY + ":file-vault-v1")`. The key is not per-user and is not stored in a KMS. Rotating `AUTHENTIQ_SECRET_KEY` without a migration makes existing files and encrypted fields unreadable.

### Database field encryption

Idea descriptions, idea notes, and commitment secrets use Fernet with a key derived from `AUTHENTIQ_SECRET_KEY` and a domain separator.

### Certificate signing

PDF certificates are generated but not digitally signed with a PKI key. They contain the fingerprint, commitment, registration ID, timestamp, and QR verification URL. A certificate is a human-readable presentation of server records, not an independently verifiable signed document.

## 7. Upload and evidence security

- File extensions are allow-listed; executable and script extensions are blocked.
- Double-extension patterns are rejected.
- The built-in scanner detects the EICAR test signature.
- Files are size-limited before and during upload.
- Chunk hashes and sizes are verified.
- Missing, reordered, or corrupted chunks block completion.
- Final files and evidence are encrypted before storage.
- Downloads are authenticated, streamed with `Cache-Control: private, no-store`, and sent with `X-Content-Type-Options: nosniff`.
- Filenames are normalized and stripped of path components.

The scanner is a development integration point. It is not a full antivirus engine and must be replaced with ClamAV or a production scanning service. Temporary plaintext chunks exist between upload and completion and should be placed on encrypted storage.

## 8. Application hardening

- CORS is restricted to configured origins; credentials are not allowed, and bearer tokens are required.
- Security headers include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a restrictive permissions policy.
- HSTS is added when `AUTHENTIQ_ENVIRONMENT=production`.
- Unhandled exceptions return a generic message and are logged server-side.
- Request bodies are validated by Pydantic with length and pattern constraints.
- Multipart uploads enforce chunk size and total size.
- SQL access uses SQLAlchemy parameter binding.
- File paths are constructed server-side from identifiers rather than user-supplied absolute paths.
- Login failures and security-relevant actions are written to the audit chain.

## 9. Audit and ledger integrity

### Audit chain

Each audit entry hashes its canonical body plus the previous entry hash. Verification recomputes the entire chain. This detects modification, insertion, or reordering by anyone who cannot also rewrite every subsequent entry.

Appends are serialized: an in-process reentrant lock guards the read-then-write sequence, and on PostgreSQL a transaction-scoped advisory lock (`pg_advisory_xact_lock`) extends that guarantee across backend workers. Without this, two concurrent requests could read the same tail entry and fork the chain.

### Simulation ledger

Each JSONL record includes:

- monotonic block number
- previous record hash
- canonical payload digest
- full record hash
- transaction ID
- timestamp, actor, entity, and event type

Appends use a process-local lock and `fsync`. Verification checks sequence, links, record hashes, and payload digests.

### Trust limits

Neither chain is a consensus system. A database or filesystem administrator can rewrite history and recompute hashes. The simulation ledger is single-node and uses only an in-process lock, so multiple backend processes can race. Use Polygon mode or anchor hashes externally when independent evidence is required. The audit chain is protected against concurrent forks by an advisory lock, but it remains a local, operator-rewriteable history.

## 10. Chain mode security

When `AUTHENTIQ_LEDGER_MODE=polygon`:

- The backend signs transactions with `AUTHENTIQ_CHAIN_PRIVATE_KEY`.
- The contract restricts writes to authorized writers.
- The backend waits for a receipt and fails closed if the transaction reverts or the RPC is unavailable.
- The contract stores identifiers and digests, not file contents.
- Amoy is a public testnet, not a production settlement network.

Operational requirements:

- Use a dedicated writer key with minimal funds.
- Store the key in a secret manager or managed signer.
- Move contract ownership to a multisig for production.
- Monitor nonce management; the adapter reads the pending transaction count.
- Do not place confidential values in on-chain strings.

## 11. Threat model and mitigations

| Threat | Mitigation | Residual risk |
| --- | --- | --- |
| Credential stuffing | Rate limits, lockout, Argon2id | No MFA; compromised passwords still work |
| Token theft through XSS | Short access lifetime, refresh rotation, React escaping | Tokens are in `localStorage`; a successful XSS can read them |
| Unauthorized resource access | Backend authorization on every route | Bugs in access helpers could over-grant |
| Malicious upload | Extension allow-list, size limits, scanner integration point | Development scanner is not full antivirus |
| Proof replay | Nonce, expiry, used challenge, one successful verification, share use limit | Shares with `max_uses > 1` allow bounded reuse |
| Commitment secret theft | Encrypted secret field, access control | Database plus secret key compromise reveals openings |
| File theft at rest | AES-256-GCM container | Key is derived from application secret, not per-tenant KMS |
| Ledger rewriting | Hash chain detection, optional on-chain anchoring | Simulation operator can rewrite and recompute |
| Audit rewriting | Hash chain detection | Same operator limitation |
| Insider access | Role checks and audit trail | Administrators with full infrastructure access remain trusted |
| Chain key compromise | Writer authorization, dedicated key | Compromised key can write until removed |
| Information leakage through public verification | Disclosure policy, private registration defaults | Misconfigured disclosure can reveal a fingerprint |
| Denial of service | Size limits, rate limits | No distributed rate limiting or request queue |
| Email interception | Not applicable; email not configured | No delivery or verification flow yet |

## 12. Known gaps

- No MFA, TOTP, passkeys, or hardware security keys.
- No email delivery, email verification, or email-based reset flow.
- No per-user or per-organization encryption keys and no KMS integration.
- No key rotation or re-encryption tooling.
- No CSRF tokens; the API uses bearer tokens rather than cookie sessions.
- Tokens are stored in `localStorage`.
- No production antivirus integration.
- No background job queue, webhook signing, or outbound notification delivery.
- No distributed rate limiter.
- No database migration history.
- No independent digital signature on PDF certificates.
- No on-chain proof verification.
- No formal third-party security audit.

## 13. Deployment hardening checklist

1. Generate a strong random `AUTHENTIQ_SECRET_KEY` and store it in a secret manager.
2. Set `AUTHENTIQ_ENVIRONMENT=production`, `AUTHENTIQ_DEBUG=false`, and restrictive CORS origins.
3. Terminate TLS and enable HSTS at the edge.
4. Use PostgreSQL with backups, least-privilege credentials, and encryption at rest.
5. Place file storage on encrypted volumes or object storage with server-side encryption.
6. Replace the built-in scanner with ClamAV or a scanning service.
7. Use a shared rate-limit store before running multiple workers.
8. Configure email delivery and remove development token responses.
9. Add MFA or passkeys before handling high-value accounts.
10. Use a dedicated chain writer key and multisig ownership in Polygon mode.
11. Monitor audit-chain verification, ledger audits, login failures, and disk usage.
12. Run dependency and container scanning in CI.

## 14. Reporting a vulnerability

Do not open a public issue containing exploit details, secrets, or private user data. Report the issue privately to the project maintainer with reproduction steps, affected version, and impact. Include only synthetic data. There is no bug bounty program.
