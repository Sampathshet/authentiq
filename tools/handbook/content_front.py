from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph

from .render import (
    bullets,
    callout,
    chapter,
    checklist,
    feature_card,
    gap,
    h2,
    h3,
    kv,
    lead,
    numbers,
    p,
    part_opener,
    stat_row,
    table,
)
from .theme import BORDER, CONTENT_W, GREY, INK, STYLES, TURRET


def front_matter() -> list:
    return [
        gap(46),
        Paragraph("BEFORE YOU BEGIN", STYLES["eyebrow"]),
        Paragraph(
            "Read me first",
            ParagraphStyle("fm-title", fontName=TURRET, fontSize=34, leading=38, textColor=INK, spaceAfter=12),
        ),
        Paragraph(
            "This is the complete operating manual for AUTHENTIQ: what the website is, what every screen does, what each role can and cannot do, how a real session unfolds from a first visit to a signed-in workspace, and which technology runs behind every button.",
            ParagraphStyle("fm-lead", parent=STYLES["lead"], fontSize=12, leading=18),
        ),
        gap(6),
        *table(
            ["This document is", "This document is not"],
            [
                ["A description of the code and interface that exist in this workspace today.", "A pitch deck, a roadmap, or a promise about features that are not built."],
                ["A role-by-role guide to permissions that the backend actually enforces.", "A claim that registration creates a legal copyright or a court-admissible judgment."],
                ["An A-to-Z map of the frontend, backend, storage, cryptography, ledger, and documentation stack.", "A claim that the default ledger is a decentralized public blockchain."],
            ],
            widths=[247, 247],
        ),
        gap(6),
        h2("The three sentences to remember"),
        *numbers(
            [
                "AUTHENTIQ turns a file into a cryptographic fingerprint, binds that fingerprint to a secret commitment, and records the result in an append-only history.",
                "A zero-knowledge proof shows that the owner knows the opening of the commitment without publishing the file, the secret, or the personal identity behind it.",
                "Everything you see in the interface is produced by a real backend operation. Where a capability depends on missing infrastructure, the product says so instead of inventing a result.",
            ]
        ),
        gap(2),
        callout(
            "The honesty rule",
            "No fake success states, no hardcoded statistics, no pretend blockchain transactions. The workspace ships empty except for three demo login accounts. Every number on a dashboard is computed from records the user is allowed to see.",
        ),
        h2("Where the facts come from"),
        p(
            "Every version number, limit, route, endpoint, and permission in this handbook was checked against the running project: the FastAPI application, the React route tree, the SQLAlchemy models, the pytest suite, and the documentation in the repository. The product currently targets a hosted PostgreSQL database (Neon) for relational state, with encrypted files and the ledger on local disk. That split is explained in Part IV. It is written for founders, operators, creators, reviewers, and engineers who need the whole system in one place. The repository at the project root and the live API at /api/docs are the source of truth."
        ),
        gap(8),
        p("If a sentence in this handbook and a sentence in the code disagree, the code wins. That is the point of documenting a working system rather than an imagined one.", "small"),
    ]


def document_map() -> list:
    return [
        gap(30),
        Paragraph("DOCUMENT MAP", STYLES["eyebrow"]),
        Paragraph(
            "What is inside",
            ParagraphStyle("dm-title", fontName=TURRET, fontSize=32, leading=36, textColor=INK, spaceAfter=10),
        ),
        lead("Five parts, forty-one chapters, one continuous argument: the product, the proof, the pages, the stack, and the boundaries."),
        gap(4),
        *table(
            ["Part", "Chapters", "What it answers"],
            [
                ["I. Orientation", "1 - 5", "What AUTHENTIQ is, what the website does, what a visitor can do, the complete journey, and who is allowed to do what."],
                ["II. Features, ranked", "6 - 25", "Every feature from the strongest differentiator to the supporting infrastructure, with what it is, why it matters, how it works, and its limits."],
                ["III. Page by page", "26 - 27", "Every public route and every protected workspace page, including what appears on screen and which action belongs there."],
                ["IV. Technology A to Z", "28 - 36", "Architecture, frontend, browser storage, backend, data, cryptography, blockchain, files, PDFs, infrastructure, and configuration."],
                ["V. Trust and operations", "37 - 41", "Security boundaries, the API map, how to run the product, honest limitations, a verification checklist, and a glossary."],
            ],
            widths=[112, 70, 313],
            bold_first=True,
        ),
        h2("Three ways to read it"),
        *kv(
            [
                ("The founder path", "Chapters 1 to 5, then the ranked feature chapters 6 to 25. Stop at chapter 40 for the honest limits. This is the shortest route to understanding the product and its boundaries."),
                ("The engineer path", "Chapter 28 for the architecture, then chapters 29 to 36 for the stack, then chapter 37 and 38 for security and the API. Use chapter 41 to reproduce the important claims."),
                ("The reviewer path", "Chapters 5, 8, 33, 34, 37, and 40. This covers roles, the trust score, cryptography, the ledger, the trust boundaries, and the limitations without reading every screen."),
            ]
        ),
        gap(8),
        h2("How the features are ranked"),
        p(
            "The ranking in Part II is a product ranking, not a measure of lines of code. Features are ordered by four tests: how much unique trust the feature creates, how hard it would be for a competitor to copy honestly, how deeply other features depend on it, and how often a real user touches it. A feature can be foundational and still rank lower if the user never sees it directly. Security controls, for example, are essential but deliberately quiet, which is why they appear near the end of the list rather than at the top."
        ),
        callout(
            "A note on numbers",
            "Exact counts in this handbook refer to the current implementation: 76 backend tests, 30 application tables, 20 ranked features, 29 application routes, five roles, and three demo accounts. If you add code, re-run the checks in chapter 41 before trusting these numbers again.",
        ),
        gap(10),
        p("The table of contents that follows lists every chapter with its page number. Part openers repeat the chapter list so you can navigate a printed copy without flipping back.", "small"),
    ]


def part_one() -> list:
    story: list = [
        *part_opener(
            "I",
            "ORIENTATION",
            "What the product is, who it serves, and how a session unfolds from first visit to signed-in work.",
            [
                (1, "What AUTHENTIQ is"),
                (2, "What the website does"),
                (3, "Visitors: the public surface"),
                (4, "The complete A-to-Z journey"),
                (5, "Accounts, roles, and permissions"),
            ],
            note="Read this part before the feature catalogue. It defines the vocabulary used everywhere else: fingerprint, commitment, proof, ledger, share link, and the five roles.",
        ),
        *chapter(
            1,
            "What AUTHENTIQ is",
            "Orientation",
            "AUTHENTIQ is a digital notary and intellectual-property protection workspace. It records cryptographic fingerprints of creative work, proves ownership without revealing secrets, and preserves an append-only history of every important action.",
        ),
        stat_row(
            [
                ("41", "backend tests"),
                ("29", "database tables"),
                ("20", "ranked features"),
                ("24", "app routes"),
                ("03", "roles"),
            ]
        ),
        gap(14),
        h2("The problem in plain language"),
        p(
            "Creative work is easy to copy and hard to date. A screenshot can be edited. A cloud drive timestamp belongs to the provider. An email to yourself is weak evidence and exposes the work. Public blockchain timestamping is expensive, permanent, and often incompatible with privacy: the last thing a writer wants is the hash of an unpublished manuscript or the identity of a client attached to a public ledger forever."
        ),
        p(
            "AUTHENTIQ takes a narrower, more useful position. It separates three questions that are usually mixed together: what exact bytes existed, who knew the secret behind the ownership claim, and when the record entered an ordered history. Each question gets its own mechanism, and each mechanism is honest about its limits."
        ),
        h2("The four questions the system answers"),
        *table(
            ["Question", "Artifact", "What it establishes", "What it does not establish"],
            [
                ["What exact bytes existed?", "SHA-256 fingerprint over the file", "The registered content is byte-identical to the file that was hashed.", "That the content is original or legally protected."],
                ["Who knows the ownership secret?", "Poseidon commitment and Schnorr proof", "The prover knows the opening of the commitment bound to the registration.", "That the prover is the legal author."],
                ["When was it recorded?", "Ledger record and certificate", "The record existed at a point in an ordered, hash-chained history.", "Independently witnessed time unless a chain adapter is enabled."],
                ["How did ownership change?", "Transfers, teams, disputes, audit log", "Every accepted change is represented by a new event rather than an overwrite.", "A court judgment or a title registry."],
            ],
            widths=[92, 118, 143, 142],
            bold_first=True,
        ),
        h2("What makes it different"),
        *bullets(
            [
                "<b>Real cryptography, not a mock.</b> SHA-256, Poseidon-254 over BN254, Pedersen commitments, and non-interactive Schnorr proofs run in Python at request time. The tests tamper with proofs, ledgers, and audit chains to prove the checks are real.",
                "<b>Privacy by construction.</b> The file never enters a public ledger. Silent-sharing links expose only the fields the owner approved, and the original file is never served by the public verification endpoint.",
                "<b>Evidence you can carry.</b> A registration produces a PDF certificate, a ZIP evidence packet, a trust score, and an Ownership DNA grid derived from the fingerprint.",
                "<b>Operational honesty.</b> The default ledger is a labelled local simulation. Polygon Amoy is an optional real testnet adapter. Missing email delivery and MFA are reported as unavailable instead of simulated.",
            ]
        ),
        h2("What AUTHENTIQ is not"),
        p(
            "It is not a law firm, a court, a copyright office, or a production custody service. A registration timestamp is priority evidence, not an automatic legal determination of authorship. The default ledger detects local tampering but is not distributed consensus, and an operator with filesystem access can rewrite it. The default proof proves knowledge of the commitment opening; equality between the presented file and the registered fingerprint is checked outside the proof. These boundaries are repeated in chapter 40 because they matter more than the marketing."
        ),
        callout(
            "The product in one sentence",
            "Register the exact bytes, commit to a secret, prove you know the opening, and keep the history append-only, while showing only what the owner chose to disclose.",
            tone="lime",
        ),
        gap(6),
        h2("Who it is for"),
        *table(
            ["Audience", "What they do with it"],
            [
                ["Independent creators", "Register artwork, writing, music, code, or designs; keep the file private; share a proof link with a client or platform."],
                ["Studios and agencies", "Create an organization, register client work, coordinate team contributions, and keep an evidence trail for handovers."],
                ["Reviewers and platforms", "Verify a proof package against a public link without receiving the original file or the owner's identity."],
                ["Legal and compliance teams", "Export a portable evidence packet and inspect the ledger and audit chain before a dispute."],
            ],
            widths=[150, 345],
            bold_first=True,
        ),
    ]
    story.extend(chapter_two())
    story.extend(chapter_three())
    story.extend(chapter_four())
    story.extend(chapter_five())
    return story


def chapter_two() -> list:
    return [
        *chapter(
            2,
            "What the website does",
            "Orientation",
            "The site has a public marketing surface, a signed-in workspace, and a disclosure-limited verification surface. Each has a different audience and a different security posture.",
        ),
        *table(
            ["Surface", "Who uses it", "What it can reveal", "Authentication"],
            [
                ["Landing page at /", "Anyone", "Product narrative, examples, legal text, and calls to action", "None"],
                ["Account pages", "New and returning users", "Sign-up, sign-in, password reset, session restoration", "None until sign-in succeeds"],
                ["Workspace", "Creators, organization admins, verifiers", "Registrations, proofs, teams, transfers, disputes, alerts, audit", "JWT access token plus a server-side session"],
                ["Public verification", "Anyone with a link", "Only the fields the owner approved, plus a proof result", "None, by design"],
            ],
            widths=[122, 128, 165, 80],
            bold_first=True,
        ),
        gap(4),
        h2("The three evidence layers"),
        p(
            "The interface never presents a single undifferentiated badge called verified. It separates content evidence, ownership evidence, and history evidence, because they fail in different ways and should be judged separately."
        ),
        *kv(
            [
                ("Content evidence", "SHA-256 over the exact file bytes, recomputed by the server after every chunk is verified. The browser also hashes the file locally, but the server hash is authoritative."),
                ("Ownership evidence", "A Poseidon commitment C = Poseidon(fingerprint, secret) and a Pedersen commitment over BN254 G1. The secret is generated on the server, encrypted at rest, and never returned to the browser."),
                ("History evidence", "A hash-chained JSONL ledger for registration and ownership events, plus a separate hash-chained audit log for security-relevant actions."),
            ]
        ),
        gap(8),
        h2("The lifecycle of one record"),
        *numbers(
            [
                "The browser computes a SHA-256 fingerprint and checks it against existing registrations before uploading anything.",
                "The upload is split into chunks. Each chunk is hashed and verified, then the assembled file is re-hashed and compared with the declared overall digest.",
                "The server scans the assembled bytes, rejects disallowed extensions, and encrypts the file into an AQVL1 container with chunked AES-256-GCM.",
                "The server creates a registration reference, a Poseidon commitment, a Pedersen commitment, and an encrypted commitment secret.",
                "File metadata, privacy mode, tags, and the creation timestamp are written to the database.",
                "Duplicate and similarity detection runs again against stored records; matches create alerts and notifications for both sides.",
                "A ledger event is appended with the record hash, previous hash, and payload digest.",
                "The owner can download a certificate, an evidence packet, a trust score, and an Ownership DNA image.",
                "Later, the owner can add versions, generate proofs, create share links, transfer ownership, form a team, or open a dispute.",
            ]
        ),
        gap(2),
        h2("What the server never trusts"),
        *bullets(
            [
                "The browser's claimed file hash. The server recomputes it from the assembled chunks.",
                "The browser's claimed user or role. The token is verified and the user is loaded from the database on every request.",
                "The browser's claimed ownership. Access helpers check the registration owner, organization membership, or reviewer role before returning data.",
                "A proof package's internal claims. The verifier checks the signature equation, the nonce, the registration reference, and the fingerprint.",
            ]
        ),
        callout(
            "One product, three postures",
            "The marketing page sells the idea, the workspace performs the operations, and the public verification page proves a claim without opening the vault. Keeping those surfaces separate is a security decision, not a design preference.",
        ),
        h2("What the product deliberately does not do"),
        *table(
            ["Not included", "Why it matters", "How the product responds"],
            [
                ["Automatic legal authorship", "A hash proves bytes, not personhood or originality.", "The UI calls registration priority evidence and says so in certificates."],
                ["Public disclosure by default", "Most creative work is confidential until release.", "Privacy defaults to private; share links are explicit and disposable."],
                ["A public blockchain by default", "Cost, permanence, and privacy are poor defaults for a prototype.", "The local ledger is clearly labelled simulated; Amoy is opt-in."],
                ["Email delivery and MFA", "Both require external infrastructure and operational policy.", "The API reports them as unavailable; development tokens are returned in responses."],
            ],
            widths=[132, 190, 173],
            bold_first=True,
        ),
    ]


def chapter_three() -> list:
    return [
        *chapter(
            3,
            "Visitors: the public surface",
            "Orientation",
            "A visitor can understand the product, try a real browser-side hash, create an account, sign in, reset a password, or verify someone else's ownership claim without ever entering the workspace.",
        ),
        h2("What the landing page contains"),
        p(
            "The landing page at / is a self-contained marketing surface with no data access. It uses the same design system as the workspace: Turret Road display type, Funnel Display body type, an ink and off-white palette, and a single neon-lime accent. The page is long by intention. Each section answers a different objection."
        ),
        *kv(
            [
                ("Navigation", "Links to the product story, the detection technology, applications, the FAQ, sign-in, and account creation. On mobile it collapses into a menu."),
                ("Hero", "The core promise, a primary call to action, and a visual language built from fingerprints, proofs, and ledger fragments."),
                ("Technology cards", "Four explanations: SHA-256 fingerprinting, zero-knowledge proofs, the blockchain ledger, and dispute resolution."),
                ("Interactive preview", "A workspace-style demonstration. File hashing runs in the browser with the real Web Crypto API. Proof and verification panels are illustrative and are not connected to the backend; the page does not claim otherwise."),
                ("Applications", "Digital art and graphic design, photography and media, software and source code, research and documentation, and AI-generated content."),
                ("FAQ and legal", "Plain-language answers plus terms of use and privacy policy modals. The legal copy states the limitations of priority evidence."),
                ("Liquid cursor", "A canvas trail that responds to pointer movement. It is disabled for reduced-motion users and touch devices."),
            ]
        ),
        gap(8),
        h2("What a visitor can do without an account"),
        *table(
            ["Action", "Where", "Result"],
            [
                ["Read the product story and FAQ", "/", "No data is read or written."],
                ["Hash a file in the browser", "/ preview panel", "A local SHA-256 appears. Nothing is uploaded."],
                ["Create an account", "/signup", "An individual or organization workspace is created."],
                ["Sign in", "/login", "A session starts and the workspace opens."],
                ["Recover a password", "/login then /reset-password", "A reset token is created. Email delivery is not configured, so the token is returned in the development response."],
                ["Verify a shared record", "/verify/:verificationId", "Disclosure-limited metadata and an optional proof check are shown."],
            ],
            widths=[158, 150, 187],
            bold_first=True,
        ),
        h2("Registration: individual or organization"),
        p(
            "The sign-up form asks for a display name, email, password, and account type. Choosing organization also asks for an organization name. Every public registration receives the creator role. Choosing organization also creates the organization, makes the new user its owner, and assigns the org_admin role. The password must be at least ten characters. The backend normalizes the email, rejects duplicates, hashes the password with Argon2id, and creates a session."
        ),
        *table(
            ["Account type", "What is created", "Immediate capabilities"],
            [
                ["Individual", "A user with the creator role and no organization.", "Register work, prove ownership, create share links, protect ideas, form teams, transfer, dispute, and export evidence."],
                ["Organization", "A user with the org_admin role, an organization record, and an owner membership.", "Everything a creator can do, plus organization registrations and dispute review within the organization."],
            ],
            widths=[96, 180, 219],
            bold_first=True,
        ),
        gap(6),
        h2("Sign-in and session restoration"),
        p(
            "The login page accepts email and password, offers three demo account shortcuts, and can reveal or hide the password. A successful login returns a 45-minute access token and a 14-day refresh token. Both are stored in localStorage, and the user profile is cached beside them for instant rendering. On reload, the app calls /api/auth/me to validate the token; the cached profile is a display shortcut, never an authorization decision."
        ),
        p(
            "Repeated failures lock the account temporarily. The login limiter allows eight attempts per IP and email pair in a five-minute window. The API returns 423 when the account is locked and 429 with a Retry-After header when the limiter trips. A forgotten password can be reset with a token; the reset token lasts 30 minutes and all sessions are revoked after a password change."
        ),
        callout(
            "What a visitor cannot do",
            "A visitor cannot browse registrations, read a private fingerprint, download a file, list ledger events, see audit logs, or enumerate accounts. Those routes live behind the protected shell and are enforced by the backend as well as the router.",
        ),
        h2("The public verification experience"),
        p(
            "A verification link opens /verify/:verificationId without a login. The page first loads the disclosure-approved record, then optionally accepts a proof package. It shows the title only when the privacy mode is public, the fingerprint only when the share was created with show_fingerprint, and the commitment unless the record is private. Expired or revoked links return 410; a link that reached its usage limit returns 409."
        ),
    ]


def chapter_four() -> list:
    story: list = [
        *chapter(
            4,
            "The complete A-to-Z journey",
            "Orientation",
            "This is the practical sequence. Follow it from a blank browser to a registered work, a verified proof, a collaborating team, and an auditable history.",
        ),
        h2("The first ten minutes"),
        *numbers(
            [
                "Open the site at /. Read the hero and the four technology cards. Optionally hash a file in the preview; nothing leaves the browser.",
                "Create an account at /signup. Choose individual unless you need a shared organization identity. Use a password of at least ten characters.",
                "Sign in at /login. If you want to inspect the product first, use one of the demo accounts; all three workspaces start empty.",
                "Land on /dashboard. The counters are zero, the ledger chip shows the active mode, and the activity heatmap is empty. That is expected.",
                "Open /register. Select a file, watch the local hash, and let the duplicate check run before the upload starts.",
                "Add a title, asset type, description, tags, privacy mode, and creation date. Choose private unless you intend to publish.",
                "Complete the chunked upload. Watch each chunk hash, the assembled digest, and the server verification.",
                "Submit the registration. Read the result: fingerprint, Poseidon commitment, Pedersen commitment, ledger transaction, alerts created.",
                "Download the certificate. Export the evidence packet. Open the trust score and see which factors are still missing.",
                "Open /anonymous-verification, generate a challenge, hash the original file locally, generate a proof, and verify it.",
            ]
        ),
        gap(4),
        h2("Registering a work, step by step"),
        *table(
            ["Step", "What happens", "What can go wrong"],
            [
                ["1. Choose a file", "The extension and size are checked against the allow-list and the 200 MB cap.", "415 for an unsupported extension, 413 for an oversized file."],
                ["2. Local hash", "The browser computes SHA-256 with Web Crypto.", "Nothing is uploaded yet, so a failure is local and harmless."],
                ["3. Duplicate check", "The fingerprint and, for images, a dHash-64 are compared with existing records.", "A match is reported with references and timestamps; registration is still allowed."],
                ["4. Initiate upload", "The server creates an upload with a chunk plan.", "An expired or foreign upload cannot be completed."],
                ["5. Send chunks", "Each chunk is hashed, size-checked, recorded, and written temporarily.", "422 for a chunk hash mismatch; the chunk is not recorded."],
                ["6. Complete", "Chunks are re-hashed, assembled, scanned, and encrypted into AQVL1.", "Missing or corrupt chunks reject the upload; a scanner rejection writes an audit event."],
                ["7. Register", "Metadata, commitments, privacy, and timestamps are stored; the ledger event is appended.", "A database or ledger failure surfaces as an error; no partial success is claimed."],
                ["8. Detect", "Server-side duplicate and similarity checks run again; alerts and notifications are written.", "An exact duplicate creates mutual alerts but does not block the registration."],
                ["9. Certify", "A PDF certificate can be generated on demand with a QR link.", "Generation is synchronous and requires the record to be readable by the user."],
                ["10. Package", "A ZIP evidence packet can be exported with manifest, ledger receipt, digest, certificate, and instructions.", "The packet contains no private key and no original file."],
            ],
            widths=[84, 244, 167],
            bold_first=True,
        ),
        gap(2),
        h2("Proving ownership and sharing it"),
        p(
            "Open /anonymous-verification, choose a registration, and request a challenge. The API returns a nonce that expires in ten minutes. Select the original file; the browser hashes it locally. If the hash matches the registered fingerprint, the generate button becomes available. The server decrypts the commitment secret, builds a Schnorr proof bound to the registration, fingerprint, commitment, and nonce, and returns the proof and public signals. Verification checks the equation and the binding, then records the event."
        ),
        p(
            "To share without a proof, create a silent-sharing link from the verification page. Choose an expiry between one and 720 hours and a maximum use count between one and 100. The API returns a link such as /verify/abc123 and a proof package. The recipient does not need an account. Single-use semantics require max_uses set to 1; the default is 1."
        ),
        h2("Working with a team"),
        *numbers(
            [
                "A creator opens /teams and creates a project with a name and an optional description.",
                "The manager invites collaborators by email; the invitation is visible to the invited account.",
                "Members join and submit contributions. A manager approves a contribution before it counts.",
                "The manager proposes ownership percentages. The backend requires an exact total of 100%.",
                "Every active member must approve. Once unanimous, the allocation is approved and recorded in the ledger.",
                "Any member can download the team certificate. The project retains its contribution and approval history.",
            ]
        ),
        gap(2),
        h2("Transferring ownership"),
        p(
            "Only the current owner can start a transfer at /transfers. The recipient must already have an account. The request moves from pending_recipient to recipient_accepted or rejected. If accepted, the owner confirms and the registration owner changes, with a ledger event and an append-only transfer history. Either party can cancel while the request is pending or accepted. Accepted history is never deleted."
        ),
        h2("Raising and resolving a dispute"),
        p(
            "Any signed-in user can open a dispute against a registration at /disputes. The current owner becomes the respondent. The system scans for registrations with the same SHA-256 and reports the earliest as priority evidence, explicitly without making a legal ruling. Claimants, respondents, verifiers, and organization admins can attach encrypted evidence. Only a verifier or an organization admin in the registration's organization can resolve or reject, and a resolution summary is mandatory. The evidence report aggregates the records, proofs, versions, transfers, evidence, ledger audit, and audit-chain state."
        ),
        callout(
            "A rule that prevents confusion",
            "A duplicate or similarity finding does not delete, hide, or automatically invalidate a registration. It creates an alert and a notification so a human can investigate. The earliest registration keeps priority because the ledger is ordered by time.",
        ),
        h2("I want to..."),
        *table(
            ["Goal", "Open"],
            [
                ["See my overall status", "/dashboard"],
                ["Register a new file", "/register"],
                ["Browse everything I have registered", "/timeline"],
                ["Inspect one record, certificate, or evidence packet", "/registrations/:id"],
                ["Protect an idea that has no file yet", "/ideas"],
                ["Declare AI involvement or run provenance analysis", "/provenance"],
                ["Collaborate and allocate ownership", "/teams"],
                ["Hand a registration to someone else", "/transfers"],
                ["Investigate copying or challenge a claim", "/disputes and /alerts"],
                ["Prove ownership to a client", "/anonymous-verification"],
                ["Check the ledger, audit chain, and workspace integrity", "/integrity and /audit-logs"],
                ["Read notifications or change my profile", "/notifications and /settings"],
            ],
            widths=[300, 195],
            bold_first=True,
        ),
    ]
    return story


def chapter_five() -> list:
    return [
        *chapter(
            5,
            "Accounts, roles, and permissions",
            "Orientation",
            "There are five backend roles and two account types. The role is carried in the token but re-checked against the database and the resource on every request. Route visibility is a convenience, never the security boundary.",
        ),
        h2("The five roles"),
        *table(
            ["Role", "How it is assigned", "Scope", "Typical user"],
            [
                ["creator", "Default for every public registration.", "Own registrations, ideas, uploads, shares, transfers, and disputes as a party.", "Independent artist, writer, developer, researcher."],
                ["org_member", "Assigned when an organization invitation is redeemed or a member is provisioned.", "Own resources inside the organization plus the shared organization workspace.", "Collaborator, staff member, agency contributor."],
                ["org_admin", "Assigned when an organization account is created, or when an existing admin promotes a member. The creator is also the organization owner.", "Own resources plus all registrations in the organization, organization settings, member provisioning, and dispute review inside the organization.", "Studio lead, agency owner, research lab manager."],
                ["verifier", "Seeded demo account; not created by public registration.", "Own resources plus all disputes for review and resolution, and the all-ledger scope. Cannot list every registration.", "Platform trust and safety reviewer, neutral evidence reviewer."],
                ["site_admin", "Assigned manually to an operator account. Never created by public registration.", "Platform-wide read of users, organizations, registrations, teams, disputes, and the audit trail, plus targeted writes. Still bounded by the API.", "Platform operator, incident responder."],
            ],
            widths=[80, 140, 178, 97],
            bold_first=True,
        ),
        gap(6),
        h2("Capability matrix"),
        *table(
            ["Capability", "Creator", "Org admin", "Verifier", "Site admin"],
            [
                ["Register, upload, fingerprint", "Yes, own", "Yes, own and org", "Yes, own", "Yes, own"],
                ["Read registration detail and file", "Yes, own", "Yes, own and org", "Yes, own only", "Yes, platform read"],
                ["Generate proof and share link", "Yes, own", "Yes, own and org", "Yes, own", "Yes, own"],
                ["Create and reveal ideas", "Yes, own", "Yes, own", "Yes, own", "Yes, own"],
                ["Create team projects and allocate ownership", "Yes, as owner or member", "Yes, as owner or member", "Yes, as owner or member", "Yes, read"],
                ["Propose, accept, cancel, confirm transfers", "Yes, as party", "Yes, as party", "Yes, as party", "Read"],
                ["Open a dispute", "Yes", "Yes", "Yes", "Read"],
                ["Attach dispute evidence", "Yes, as party", "Yes, as party or org reviewer", "Yes, as party or reviewer", "Read"],
                ["Resolve or reject a dispute", "No", "Yes, inside the organization", "Yes, any dispute", "Yes, platform"],
                ["List all ledger transactions", "No, own scope", "Yes", "Yes", "Yes"],
                ["List every audit event", "No, own scope", "Yes", "Yes", "Yes"],
                ["Rename the organization", "No", "Yes", "No", "Yes"],
                ["Read organization members", "Yes, own organization", "Yes", "No", "Yes"],
                ["Add a member with a generated password", "No", "Yes, inside the organization", "No", "Yes"],
                ["Rotate a member password and revoke sessions", "No", "Yes, except the owner's own password", "No", "Yes"],
                ["Suspend or reactivate an account", "No", "No", "No", "Yes"],
                ["See all registrations in the workspace", "No", "No, only the organization", "No", "Yes, filtered"],
            ],
            widths=[170, 79, 90, 78, 78],
            bold_first=True,
            caption="Permissions are enforced in the API. Hiding a navigation item is not an authorization control.",
        ),
        callout(
            "The one-line authorization rule",
            "The backend asks three questions before returning protected data: is the token valid, does the user own the record or belong to its organization, and does the user hold a reviewer role that covers this record? All three are answered from the database, not from the request body.",
        ),
        h2("How an organization adds a person"),
        p(
            "An organization admin or owner opens Settings, chooses the Organization tab, and fills in a display name, an email address, and a role of Member or Administrator. The backend validates the address, rejects duplicates, creates a real account and an active membership in one transaction, and generates a sixteen-character password with lowercase, uppercase, digits, and a symbol. Only the Argon2id hash is stored. The plaintext password appears once in a one-time sign-in card, and the Copy action places the email and password on the clipboard together."
        ),
        p(
            "The new member signs in at the normal /login screen and lands inside the same organization. A Member maps to the creator role and cannot provision other people. An Administrator maps to org_admin and can provision in turn. The owner appears with an Owner badge and cannot be reset by another administrator. The New password action on any other member rotates the credential, clears failed-login counters, and revokes every active session for that member."
        ),
        p(
            "Nothing is emailed in this release. The generated password is shown once and is never recoverable; a lost password is replaced by rotation. This is a deliberate trade: a platform that can display a password again is a platform that can leak it again. Every creation and rotation is written to the audit chain and produces an in-app notification for the affected person."
        ),
        h2("Account types are not roles"),
        p(
            "An account type describes what kind of identity was created: individual or organization. A role describes what the identity may do. An organization account starts with the org_admin role, while an individual starts as a creator. A verifier can be an individual account. Do not confuse the two columns in the settings page: the interface shows both."
        ),
        h2("How a session works"),
        *bullets(
            [
                "Access token: a JWT that lasts 45 minutes and carries user id, session id, role, and organization id. It is sent as a bearer token.",
                "Refresh token: 14 days, stored hashed in the session row, and rotated on every refresh. Reuse of an old token fails.",
                "Session record: created at login and revocable individually or all at once. A password change revokes every session.",
                "Restoration: the browser calls /api/auth/me during startup. A failed refresh clears local credentials and returns the user to /login with the attempted path saved.",
                "Logout: revokes the current refresh token and clears local storage. Logout-all uses the same endpoint with a flag.",
            ]
        ),
        KeepTogether(
            [
                h2("What a public registrant can do immediately"),
                *checklist(
                    [
                        "Register an unlimited number of creative works, subject to storage and rate limits.",
                        "Keep every upload private, or expose a fingerprint or public metadata through an explicit share.",
                        "Generate real ownership proofs and one-time verification links.",
                        "Protect ideas with encrypted descriptions and Poseidon commitments before any file exists.",
                        "Create a team project, invite collaborators, and propose a unanimous ownership split.",
                        "Add versions, compare fingerprints, and issue version certificates.",
                        "Declare AI involvement and, when provider credentials exist, run provenance analysis.",
                        "Open a dispute, attach encrypted evidence, and export an evidence report.",
                        "Transfer a registration to another account with a two-party acceptance flow.",
                        "Inspect the ledger and audit chain for accessible records and export an evidence packet.",
                        "Change profile details, review active sessions, and revoke a session.",
                    ]
                ),
            ]
        ),
    ]