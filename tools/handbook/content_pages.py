from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from .render import (
    bullets,
    callout,
    chapter,
    gap,
    h2,
    h3,
    kv,
    lead,
    p,
    part_opener,
    table,
)
from .theme import INK, STYLES, TURRET


def part_three() -> list:
    return [
        *part_opener(
            "III",
            "PAGE BY PAGE",
            "Every public route and every protected workspace page, in the order a real session encounters them. Use this part as a map when you are testing the product or training someone else.",
            [
                (26, "Public pages"),
                (27, "Workspace pages"),
            ],
            note="This part describes what appears on screen and which action belongs there. It does not repeat the technical mechanics from Part II unless the page depends on them.",
        ),
        *chapter(
            26,
            "Public pages",
            "Page guide",
            "Eight routes are open to anyone: the landing page, sign-in, sign-up, password reset, public verification, the public records registry, the organization join page, and the not-found page.",
        ),
        *table(
            ["Route", "Purpose", "Authentication"],
            [
                ["/", "Marketing site and interactive product preview.", "None"],
                ["/login", "Sign in, use a demo account, or start password recovery.", "None"],
                ["/signup", "Create an individual or organization account.", "None"],
                ["/reset-password", "Consume a reset token and choose a new password.", "None"],
                ["/verify/:verificationId", "Disclosure-limited public verification and proof check.", "None"],
                ["/verify", "Redirect to the signed-in verification page.", "None, but the target is protected"],
                ["/records", "Public records registry of records whose owner chose the Public disclosure level.", "None"],
                ["/join", "Redeem an organization invitation code and join that organization.", "None to view, sign-in to accept"],
                ["*", "Not-found page with routes back to safety.", "None"],
            ],
            widths=[160, 265, 70],
            bold_first=True,
        ),
        gap(2),
        h2("Landing page  ·  /"),
        p(
            "The landing page is a long editorial narrative, not a dashboard preview. It opens with the core promise and a primary call to action, then walks through the problem, the four technologies, the workflow, the applications, and the FAQ. The navigation links to the same anchors and to sign-in and sign-up."
        ),
        *bullets(
            [
                "<b>Hero and navigation.</b> The AUTHENTIQ wordmark, product promise, and calls to action. The mobile menu collapses the anchors.",
                "<b>Technology cards.</b> SHA-256 fingerprinting, zero-knowledge proofs, blockchain ledger, and dispute resolution, each with a small explanatory diagram.",
                "<b>Workspace preview.</b> A simulated workspace that hashes a selected file with the real Web Crypto API. The proof and verification panels are illustrative and are not connected to the API; the page does not claim they are.",
                "<b>Applications.</b> Art and design, photography and media, software and source code, research and documentation, and AI-generated content.",
                "<b>FAQ and legal modals.</b> Plain-language answers, terms of use, and a privacy policy that names the limitations.",
                "<b>Motion and accessibility.</b> The liquid cursor is disabled for reduced-motion users and touch devices; focus states use the lime accent.",
            ]
        ),
        gap(4),
        h2("Sign in  ·  /login"),
        p(
            "A focused card with email, password, show or hide control, and a primary sign-in button. Three demo account shortcuts fill the form without submitting. A forgot-password dialog requests an email and displays the development reset token when email delivery is unavailable."
        ),
        *kv(
            [
                ("Success", "Tokens and user profile are stored, the refresh timer starts, and the user is sent to the attempted page or /dashboard."),
                ("Failure", "A clear error is shown. Repeated failures lock the account; the API returns 423 or 429."),
                ("Restoration", "If a session already exists, /api/auth/me runs first and the page redirects to the workspace."),
                ("Demo", "demo@authentiq.dev, verifier@authentiq.dev, maya@authentiq.dev. The cards expose the passwords for evaluation."),
            ]
        ),
        gap(6),
        h2("Create an account  ·  /signup"),
        p(
            "The form switches between individual and organization. Both ask for display name, email, password, and confirmation. Organization adds a name field and explains that the creator becomes the organization admin. The password minimum is ten characters; the client validates before the request and the server enforces the same rule."
        ),
        *bullets(
            [
                "On success, the session is created immediately and the user lands in the workspace.",
                "The new account starts empty: no registrations, ideas, teams, alerts, transfers, disputes, or ledger events.",
                "Organization sign-up creates the organization, the owner membership, and the org_admin role in the same flow.",
                "The legal copy is available from the form; acceptance is part of account creation.",
            ]
        ),
        gap(4),
        h2("Reset password  ·  /reset-password"),
        p(
            "The page accepts a reset token and a new password. In this deployment there is no email provider, so the token is returned in the forgot-password response and can be pasted here. The token lasts 30 minutes. A successful reset revokes every existing session, which is the correct behavior after a suspected compromise."
        ),
        h2("Public verification  ·  /verify/:verificationId"),
        p(
            "This is the page a client or platform sees. It does not require an account and never serves the original file. It loads the disclosure-approved metadata, then optionally accepts a proof package pasted into a text area or supplied by the share flow."
        ),
        *table(
            ["Element", "When it appears", "Why"],
            [
                ["Title", "Only for a public record", "Titles can reveal unreleased work."],
                ["Fingerprint", "Only when the share enabled it", "A fingerprint can be correlated with other databases."],
                ["Commitment", "Unless the record is private", "The commitment is the public half of the ownership claim."],
                ["Ledger transaction", "When a record exists", "Shows the ordered history reference."],
                ["Proof result", "After a package is submitted", "Returns valid or invalid with a reason."],
                ["Owner identity", "Never", "The public endpoint does not expose personal identity."],
            ],
            widths=[150, 175, 170],
            bold_first=True,
        ),
        gap(2),
        callout(
            "The public page is intentionally boring",
            "It shows a small set of facts, a proof result, and a clear privacy note. It is not a second workspace, and it cannot be used to enumerate records or accounts.",
        ),
        h2("Public records  ·  /records"),
        p(
            "A public registry of the records whose owners deliberately chose the Public disclosure level. It needs no account, and it lists only those records. Search, asset-type filtering, and sorting are server-side. Private records and fingerprint-only records are never enumerated here; they stay reachable only through their reference or a silent-sharing link."
        ),
        *bullets(
            [
                "<b>Each entry shows</b> the title, creator display name, organization or team affiliation, asset type, registration date, and the public fingerprint.",
                "<b>Descriptions are truncated</b> to a preview length so the registry cannot be scraped for full text.",
                "<b>Searching returns only public records.</b> The query is applied inside the disclosure filter, not after it.",
            ]
        ),
        h2("Join an organization  ·  /join"),
        p(
            "The redemption page for an organization invitation. The admin issues a one-time code and shares the link that carries it. The recipient opens the page, sees which organization and role the code grants, signs in if needed, and accepts. Accepting creates the membership and the org_member role in one transaction, and the code is cleared so it cannot be reused."
        ),
        h2("Not found  ·  *"),
        p(
            "An unknown path renders a calm not-found page with a route back to the landing page and, when signed in, the dashboard. It does not leak whether a protected resource exists."
        ),
    ]


def part_three_workspace() -> list:
    story: list = [
        *chapter(
            27,
            "Workspace pages",
            "Page guide",
            "Nineteen protected pages share one shell: a grouped sidebar, global search, notifications, a ledger status chip, and a user menu. Every page is reachable from the sidebar, but the backend still enforces access.",
        ),
        h2("The application shell"),
        *kv(
            [
                ("Workspace group", "Dashboard, Register creation, Creative timeline, Idea vault, AI provenance."),
                ("Collaboration group", "Teams, Transfers, Disputes."),
                ("Trust center group", "Verify ownership, Integrity center, Alerts, Ledger and audit, Notifications, Settings."),
                ("Header", "Global search with grouped results; notification bell with unread count; ledger mode chip; user menu."),
                ("Mobile", "The sidebar becomes a drawer. The header keeps search and the account menu."),
            ]
        ),
        gap(8),
        *table(
            ["Route", "Page", "Primary job"],
            [
                ["/dashboard", "Dashboard", "Summarize counts, activity, ledger state, and pending work."],
                ["/register", "Register creation", "Upload, verify, and register a new work."],
                ["/timeline", "Creative timeline", "Browse, filter, search, and sort registrations."],
                ["/registrations/:id", "Registration detail", "Inspect a record and download certificate, file, or packet."],
                ["/ideas", "Idea vault", "Protect ideas before a file exists."],
                ["/ideas/:ideaRef", "Idea detail", "Read, revise, reveal, and certify one idea."],
                ["/provenance", "AI provenance", "Declare AI involvement and inspect analysis availability."],
                ["/teams", "Teams", "Create, join, and open team projects."],
                ["/teams/:id", "Team detail", "Members, contributions, allocation, certificate."],
                ["/transfers", "Transfers", "Propose, accept, reject, cancel, or confirm a transfer."],
                ["/disputes", "Disputes", "Open and filter disputes."],
                ["/disputes/:id", "Dispute detail", "Read the claim, attach evidence, resolve if authorized."],
                ["/anonymous-verification", "Verify ownership", "Generate a challenge, proof, or share link."],
                ["/alerts", "Alerts", "Investigate duplicate and similarity findings."],
                ["/notifications", "Notifications", "Read, filter, open, and dismiss system events."],
                ["/audit-logs", "Ledger and audit", "Inspect transactions and audit entries, run verification."],
                ["/integrity", "Integrity center", "Recompute chains and workspace integrity."],
                ["/settings", "Settings", "Profile, organization, sessions, and security report."],
                ["/organization", "Organization workspace", "Shared organization records, members, and invitations."],
                ["/admin", "Site administration", "Platform users, organizations, disputes, and audit trail."],
            ],
            widths=[140, 118, 237],
            bold_first=True,
        ),
        gap(2),
        h2("Dashboard  ·  /dashboard"),
        p(
            "The first page after sign-in. Eight cards show total creations, verified records, protected ideas, team projects, pending transfers, active disputes, security alerts, and verified proofs. Below them sit a 26-week activity heatmap, recent registrations, and a ledger status panel."
        ),
        *bullets(
            [
                "<b>What you can do:</b> jump to any card's page, refresh the summary, or open a recent registration.",
                "<b>Empty state:</b> zeros and a clear prompt to register the first work. No sample records are invented.",
                "<b>What it reads:</b> /api/dashboard/summary and /api/dashboard/activity, scoped to your access.",
            ]
        ),
        h2("Register creation  ·  /register"),
        p(
            "A single guided form. Choose a file, watch the local SHA-256, wait for the duplicate check, then supply title, asset type, description, tags, privacy mode, and an optional creation date. The upload runs in chunks with a visible digest, and the result card shows the fingerprint, both commitments, the ledger transaction, privacy, and the number of alerts created."
        ),
        *bullets(
            [
                "<b>Before upload:</b> extension and size validation, local hash, duplicate and perceptual check.",
                "<b>During upload:</b> per-chunk progress and verification. A failed chunk can be retried without restarting the file.",
                "<b>After registration:</b> download the certificate, open the record, or start another registration.",
                "<b>Failure states:</b> unsupported extension, oversized file, hash mismatch, scanner rejection, or a server error. Each is shown as a specific error, not a generic success.",
            ]
        ),
        h2("Creative timeline  ·  /timeline"),
        p(
            "The library view. Each card shows the title, asset type, status, registration reference, fingerprint, file name, and date. Search matches title, reference, fingerprint, or file name. Filters cover asset type and sort order, and pagination is server-side."
        ),
        h2("Registration detail  ·  /registrations/:id"),
        p(
            "The evidence workbench. It displays the registration reference, SHA-256, Poseidon commitment, Pedersen commitment, ledger transaction, file metadata, privacy, status, registered date, and creation date. Actions include preview, download original, download certificate, export evidence packet, and refresh."
        ),
        *bullets(
            [
                "The trust card explains the 0-100 score factor by factor, including penalties.",
                "The Ownership DNA panel renders the fingerprint as a deterministic grid and offers an SVG download.",
                "Version history, proof history, alerts, and ledger linkage are visible where applicable.",
                "Access is limited to the owner, the organization, or an authorized reviewer scope.",
            ]
        ),
        h2("Idea vault  ·  /ideas"),
        p(
            "A grid of protected ideas. Each card shows the title, commitment, privacy, status, and update time. Creating an idea requires a title and a description of at least ten characters, plus a privacy level: private, timestamp_only, or organization."
        ),
        h2("Idea detail  ·  /ideas/:ideaRef"),
        p(
            "The full idea record: reference, commitment, ledger transaction, privacy, status, revisions, encrypted notes, and reveal state. Actions add a revision, update notes, reveal the idea, download the certificate, or export the evidence package. Reveal is deliberate and recorded."
        ),
        h2("AI provenance  ·  /provenance"),
        p(
            "A list of provenance declarations with model, tool, declared AI state, confidence, and ledger reference. The form records AI involvement, model name, tool or platform, a prompt commitment (the raw prompt is not stored by that field), human contribution, editing details, and notes. Analysis only appears when a real provider is configured."
        ),
        h2("Teams  ·  /teams and /teams/:id"),
        p(
            "The list shows projects you own or have joined, with status and an ownership ledger transaction. A Pending invitations card lists projects that invited your email address, each with an Accept invitation button. Below it, Join with an invitation code is a single field: paste the code the team owner shared and your membership activates with the role the owner assigned, then you land on the project. The detail page shows members, roles, contributions, allocation state, your role, and the certificate action. Managers can invite, approve contributions, and propose percentages; every active member must approve a 100 percent allocation. An invite code is single-use and is cleared once redeemed."
        ),
        h2("Transfers  ·  /transfers"),
        p(
            "Two lists: incoming and outgoing. Each request shows the registration, the other party, the current state, the message, the ledger transaction, and only the actions valid for that state. Creating a transfer requires an owned registration and the recipient's email address; the recipient must already have an account."
        ),
        h2("Disputes  ·  /disputes and /disputes/:id"),
        p(
            "The list shows disputes you are a party to or are authorized to review, with status and filters. Raising a dispute requires a registration, a reason, and a description of at least twenty characters. The detail page shows the parties, the earliest matching registration, encrypted evidence, status controls, and a downloadable JSON evidence report."
        ),
        h2("Verify ownership  ·  /anonymous-verification"),
        p(
            "The proof workbench. Select a registration, request a challenge, choose the original file, and watch the local hash compare with the registered fingerprint. When they match, generate and verify the proof. The same page creates a silent-sharing link with an expiry and use limit and displays the proof package."
        ),
        *bullets(
            [
                "Challenge nonce and expiry are shown explicitly.",
                "A mismatch blocks proof generation and explains why.",
                "The result includes the validity message, public signals, and recent proofs.",
                "A share link is displayed once and can be copied; existing links can be listed and revoked.",
            ]
        ),
        h2("Alerts  ·  /alerts"),
        p(
            "An investigation queue. Each alert shows its type, status, matched record, fingerprint, similarity data, and notes. Actions move it to under_review, resolved, or dismissed and record investigation notes. Alerts are findings, not verdicts."
        ),
        h2("Notifications  ·  /notifications"),
        p(
            "The inbox. Filter by category or unread state, mark one or all as read, open the related record, or dismiss an item. Notifications are created inside the same transaction as the event that triggered them."
        ),
        h2("Ledger and audit  ·  /audit-logs"),
        p(
            "Two tabs. The ledger tab lists transactions with block number, type, actor, entity, record hash, and timestamp, and offers inspection. The audit tab lists security events with actor, action, entity, and record hash. Buttons verify the ledger and the audit chain and report the first mismatch if any."
        ),
        h2("Integrity center  ·  /integrity"),
        p(
            "The diagnostic page. Four headline tiles show ledger chain, audit chain, workspace digest, and open issues. Below them are the last hashes, storage presence, ledger linkage, duplicate groups, exposure counts, and a record-level map. Recheck recomputes everything from the source."
        ),
        h2("Settings  ·  /settings"),
        p(
            "Profile editing, account metadata, organization details and members, active sessions, and a security report. Display name and avatar color are editable. Sessions can be revoked individually. The security section reports Argon2id, token lifetimes, encryption, audit state, and the honest unavailability of MFA and passkeys."
        ),
        p(
            "Organization admins and owners get a provisioning panel. Add a member with a display name, email address, and role of Member or Administrator. The backend creates the account immediately, generates a sixteen-character password that mixes lowercase, uppercase, digits, and symbols, and returns it once in a one-time sign-in card. Copy sends both the email and password to the clipboard. The plaintext password is never stored and cannot be shown again. Email delivery is not configured, so the admin shares the credentials directly and should use a secure channel."
        ),
        p(
            "Each row in the member list carries New password. Rotating a member password generates a fresh one-time credential, clears failed-login counters, and revokes every active session for that member. The owner's own password is excluded from admin reset. Every provisioning and rotation action is written to the audit chain and triggers a notification for the affected member."
        ),
        h2("Organization workspace  ·  /organization"),
        p(
            "The shared organization view. It lists the organization's registrations with their proof and certificate state, the member roster with roles and statuses, and the outstanding invitations. A manager can issue an invitation, copy the one-time code, or revoke an invitation that was never accepted."
        ),
        h2("Site administration  ·  /admin"),
        p(
            "The operator console, gated on the site_admin role at the API rather than in the menu. Tabs cover platform overview counts, user accounts and their status, organizations and their members, disputes awaiting a decision, registrations across the platform, and the audit trail. Actions are deliberately narrow: suspend or reactivate an account, resolve a dispute, and act on an organization. Every write is audited with the operator identity."
        ),
        gap(6),
        callout(
            "A page is not a permission",
            "The sidebar hides routes a user cannot use, but the real check is in the API. Opening /audit-logs without a token redirects to /login; calling the endpoint without a valid token returns 401, and with an insufficient role returns 403.",
        ),
    ]
    return story
