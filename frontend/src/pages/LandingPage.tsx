import { type FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

type VisualKind = "fingerprint" | "zkp" | "ledger" | "dispute";

const detectionCards: {
  number: string;
  title: string;
  tier: string;
  text: string;
  visual: VisualKind;
}[] = [
  {
    number: "01",
    title: "SHA-256 Fingerprinting",
    tier: "Core",
    text: "Cryptographically digests any digital file into a fixed-size SHA-256 fingerprint that uniquely represents its contents.",
    visual: "fingerprint",
  },
  {
    number: "02",
    title: "Zero-Knowledge Proofs",
    tier: "Core",
    text: "Proves ownership of a work without revealing the original file, using ZKP circuits built with Circom and snarkjs.",
    visual: "zkp",
  },
  {
    number: "03",
    title: "Blockchain Ledger",
    tier: "Strong",
    text: "Registers fingerprints and proof commitments on an immutable, append-only ledger with verifiable timestamps.",
    visual: "ledger",
  },
  {
    number: "04",
    title: "Dispute Resolution",
    tier: "Stretch",
    text: "Resolves conflicting ownership claims by comparing proof validation results and ledger timestamps.",
    visual: "dispute",
  },
];

const faqs = [
  {
    q: "Is my original file stored or shared?",
    a: "No. AUTHENTIQ never stores or transmits your original work. Only its SHA-256 fingerprint and a Zero-Knowledge Proof commitment are registered on the ledger.",
  },
  {
    q: "How is ownership proven without revealing the work?",
    a: "Zero-Knowledge Proofs allow you to demonstrate that you know the pre-image of a registered fingerprint without disclosing the file itself.",
  },
  {
    q: "What file types can be registered?",
    a: "Any digital work — documents, images, source code, research papers, audio, video, and AI-generated content can be fingerprinted and registered.",
  },
  {
    q: "What happens if two people claim the same work?",
    a: "The ledger's append-only timestamps determine which registration occurred first. The earliest valid fingerprint and proof commitment takes precedence.",
  },
  {
    q: "Is this a real blockchain transaction?",
    a: "No. This is an illustrative frontend. Actual SHA-256, ZKP and blockchain operations are handled by backend modules and are not connected unless VITE_API_BASE_URL is configured.",
  },
  {
    q: "Can AI-generated works be registered?",
    a: "Yes. AI-generated images, text, and code can be registered as digital works, with their fingerprints recorded on the ledger.",
  },
];

const applications = [
  {
    title: "Digital Art & Graphic Design",
    items: ["Illustrations.", "Logos.", "Digital paintings."],
    type: "art",
  },
  {
    title: "Photography & Media",
    items: ["Photographs.", "Video works.", "Audio recordings."],
    type: "photo",
  },
  {
    title: "Software & Source Code",
    items: ["Source repositories.", "Modules.", "Build artifacts."],
    type: "code",
  },
  {
    title: "Research & Documentation",
    items: ["Papers.", "Theses.", "Technical reports."],
    type: "research",
  },
  {
    title: "AI-Generated Content",
    items: ["Model outputs.", "Prompts.", "Generated images."],
    type: "ai",
  },
];

function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return (
    <span className={diagonal ? "arrow diagonal" : "arrow"} aria-hidden="true">
      →
    </span>
  );
}

function LiquidCursor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const touchDevice =
      window.matchMedia("(pointer: coarse)").matches || navigator.maxTouchPoints > 0;
    if (!canvas || !context || reducedMotion.matches || touchDevice) return;

    type TrailPoint = { x: number; y: number; time: number; width: number };
    const lifetime = 420;
    const trails: TrailPoint[][] = [];
    let width = 0;
    let height = 0;
    let frame = 0;
    let currentTrail: TrailPoint[] | null = null;
    let lastX = 0;
    let lastY = 0;
    let lastWidth = 13;
    let lastInputTime = 0;
    let pointSequence = 0;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const renderSegment = (trail: TrailPoint[], index: number, now: number, seed: number) => {
      const previous = trail[Math.max(0, index - 2)];
      const from = trail[index - 1];
      const to = trail[index];
      const next = trail[Math.min(trail.length - 1, index + 1)];
      const age = now - (from.time + to.time) / 2;
      const remaining = Math.max(0, Math.min(1, 1 - age / lifetime));
      if (remaining <= 0) return;
      const fade = remaining * remaining * (3 - 2 * remaining);
      const widthVariation = Math.sin(seed * 1.83 + from.x * 0.018) * 1.25;
      const controlOneX = from.x + (to.x - previous.x) / 6;
      const controlOneY = from.y + (to.y - previous.y) / 6;
      const controlTwoX = to.x - (next.x - from.x) / 6;
      const controlTwoY = to.y - (next.y - from.y) / 6;

      context.lineCap = "round";
      context.lineJoin = "round";
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.bezierCurveTo(controlOneX, controlOneY, controlTwoX, controlTwoY, to.x, to.y);
      context.strokeStyle = `rgba(168,253,2,${fade * 0.12})`;
      context.lineWidth =
        (previous.width + from.width * 3 + to.width * 3 + next.width) / 8 + 4 + widthVariation;
      context.stroke();

      context.beginPath();
      context.moveTo(from.x, from.y);
      context.bezierCurveTo(controlOneX, controlOneY, controlTwoX, controlTwoY, to.x, to.y);
      context.strokeStyle = `rgba(168,253,2,${fade * 0.72})`;
      context.lineWidth =
        Math.max(1, (previous.width + from.width + to.width + next.width) / 4 + widthVariation * 0.35);
      context.stroke();
    };

    const draw = (now: number) => {
      frame = 0;
      context.clearRect(0, 0, width, height);
      for (let trailIndex = trails.length - 1; trailIndex >= 0; trailIndex -= 1) {
        const trail = trails[trailIndex];
        while (trail.length && now - trail[0].time >= lifetime) trail.shift();
        if (trail.length < 2) {
          if (!trail.length) trails.splice(trailIndex, 1);
          continue;
        }
        for (let index = 1; index < trail.length; index += 1) {
          renderSegment(trail, index, now, index + trailIndex * 31);
        }
      }
      if (trails.length) frame = requestAnimationFrame(draw);
    };

    const requestAnimation = () => {
      if (!frame) frame = requestAnimationFrame(draw);
    };

    const handlePointerMove = (event: PointerEvent) => {
      const now = performance.now();
      const elapsed = Math.max(8, now - lastInputTime);
      const rawDistance = Math.hypot(event.clientX - lastX, event.clientY - lastY);
      if (!currentTrail || !lastInputTime || elapsed > 120 || rawDistance > 180) {
        currentTrail = [{ x: event.clientX, y: event.clientY, time: now, width: 14 }];
        trails.push(currentTrail);
        lastX = event.clientX;
        lastY = event.clientY;
        lastWidth = 14;
        lastInputTime = now;
        requestAnimation();
        return;
      }

      const inputSpeed = rawDistance / elapsed;
      const smoothing = Math.min(0.94, 0.76 + inputSpeed * 0.06);
      const x = lastX + (event.clientX - lastX) * smoothing;
      const y = lastY + (event.clientY - lastY) * smoothing;
      const distance = Math.hypot(x - lastX, y - lastY);
      if (distance < 0.8) return;
      const targetWidth = Math.max(6, Math.min(18, 18 - inputSpeed * 4.65));
      const nextWidth = lastWidth * 0.62 + targetWidth * 0.38;
      const steps = Math.min(64, Math.max(1, Math.ceil(distance / 2.5)));
      for (let step = 1; step <= steps; step += 1) {
        const progress = step / steps;
        currentTrail.push({
          x: lastX + (x - lastX) * progress,
          y: lastY + (y - lastY) * progress,
          time: lastInputTime + (now - lastInputTime) * progress,
          width:
            (lastWidth + (nextWidth - lastWidth) * progress) *
            (1 + Math.sin((pointSequence + step) * 0.31) * 0.022),
        });
      }
      pointSequence += steps;
      lastX = x;
      lastY = y;
      lastWidth = nextWidth;
      lastInputTime = now;
      requestAnimation();
    };
    const endTrail = () => {
      currentTrail = null;
      lastInputTime = 0;
    };
    const handleMotionChange = () => {
      if (reducedMotion.matches) {
        trails.length = 0;
        currentTrail = null;
        if (frame) cancelAnimationFrame(frame);
        frame = 0;
        context.clearRect(0, 0, width, height);
      }
    };

    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.addEventListener("pointerleave", endTrail);
    document.addEventListener("pointercancel", endTrail);
    reducedMotion.addEventListener("change", handleMotionChange);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerleave", endTrail);
      document.removeEventListener("pointercancel", endTrail);
      reducedMotion.removeEventListener("change", handleMotionChange);
    };
  }, []);

  return <canvas ref={canvasRef} className="liquid-cursor" aria-hidden="true" />;
}

function TechnicalVisual({ kind }: { kind: VisualKind }) {
  if (kind === "fingerprint") {
    return (
      <svg viewBox="0 0 340 170" role="img" aria-label="SHA-256 fingerprint diagram">
        <rect x="40" y="20" width="110" height="130" rx="8" />
        <rect x="50" y="35" width="22" height="100" rx="3" />
        <rect x="78" y="30" width="22" height="110" rx="3" />
        <rect x="106" y="40" width="22" height="100" rx="3" />
        <path d="M92 105Q110 125 128 105" />
        <circle className="fill-lime" cx="150" cy="85" r="18" />
        <text className="light-text" x="150" y="91">
          #
        </text>
        <text x="200" y="140">
          a3f7...9d1e
        </text>
      </svg>
    );
  }
  if (kind === "zkp") {
    return (
      <svg viewBox="0 0 340 170" role="img" aria-label="Zero-knowledge proof verification diagram">
        <circle cx="85" cy="85" r="35" />
        <circle className="fill-lime" cx="85" cy="85" r="22" />
        <path d="M75 85 95 75 115 95" />
        <path d="M255 55c0 28-34 50-76 50s-76-22-76-50 34-50 76-50 76 22 76 50" />
        <text x="55" y="145">
          COMMITMENT
        </text>
        <text x="200" y="145">
          PROOF
        </text>
        <text x="200" y="162">
          VERIFIED
        </text>
      </svg>
    );
  }
  if (kind === "ledger") {
    return (
      <svg viewBox="0 0 340 170" role="img" aria-label="Blockchain ledger chain diagram">
        {[
          [60, 85],
          [145, 85],
          [230, 85],
          [315, 85],
        ].map(([cx, cy], i) => (
          <g key={i}>
            <circle cx={cx} cy={cy} r="16" />
            <circle className={i === 0 ? "fill-lime" : "fill-dark"} cx={cx} cy={cy} r="10" />
            {i < 3 && <path d={`M${cx + 16} ${cy} L${cx + 34} ${cy}`} />}
          </g>
        ))}
        <text x="20" y="60">
          BLOCK 1
        </text>
        <text x="105" y="60">
          BLOCK 2
        </text>
        <text x="190" y="60">
          BLOCK 3
        </text>
        <text x="275" y="60">
          BLOCK 4
        </text>
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 340 170" role="img" aria-label="Dispute resolution comparison diagram">
      <rect x="40" y="45" width="90" height="80" rx="6" />
      <rect x="210" y="45" width="90" height="80" rx="6" />
      <path d="M135 45L155 65M135 125L155 105" />
      <circle className="fill-lime" cx="85" cy="85" r="14" />
      <circle className="fill-dark" cx="255" cy="85" r="14" />
      <text x="48" y="140">
        CLAIM A
      </text>
      <text x="218" y="140">
        CLAIM B
      </text>
      <text x="48" y="158">
        EARLIER TS
      </text>
      <text x="218" y="158">
        LATER TS
      </text>
    </svg>
  );
}

function HeroNetwork() {
  return (
    <div className="hero-proof">
      <img src="/favicon.png" alt="AUTHENTIQ identity mark" />
    </div>
  );
}

function DetectionCard({ card }: { card: (typeof detectionCards)[number] }) {
  return (
    <article className="detection-card">
      <div className="card-surface">
        <div className="card-visual">
          <TechnicalVisual kind={card.visual} />
        </div>
      </div>
      <div className="card-copy">
        <div className="card-index">{card.number}</div>
        <div>
          <div className="tier">{card.tier}</div>
          <h3>{card.title}</h3>
          <p>{card.text}</p>
        </div>
      </div>
    </article>
  );
}

function AccountAccess({
  mode,
  onSwitch,
}: {
  mode: "register" | "login";
  onSwitch: (mode: "register" | "login") => void;
}) {
  const navigate = useNavigate();
  const [message, setMessage] = useState<string | null>(null);
  const [role, setRole] = useState<"creator" | "verifier">("creator");

  useEffect(() => {
    setMessage(null);
  }, [mode]);

  return (
    <>
      <div className="account-modal-heading">
        <span className="section-mark">{mode === "register" ? "NEW ACCOUNT" : "EXISTING ACCOUNT"}</span>
        <h2>{mode === "register" ? "REGISTER." : "LOGIN."}</h2>
        <p>
          {mode === "register"
            ? "Create an account to register and verify your digital work."
            : "Log in to continue to your AUTHENTIQ workspace."}
        </p>
      </div>
      <div className="account-roles" role="group" aria-label="Account role">
        <span>Choose workspace</span>
        <button
          className={role === "creator" ? "active" : ""}
          type="button"
          aria-pressed={role === "creator"}
          onClick={() => setRole("creator")}
        >
          Creator
        </button>
        <button
          className={role === "verifier" ? "active" : ""}
          type="button"
          aria-pressed={role === "verifier"}
          onClick={() => setRole("verifier")}
        >
          Verifier
        </button>
      </div>
      <form
        key={`${mode}-${role}`}
        className="account-form"
        onSubmit={(event) => {
          event.preventDefault();
          setMessage(
            mode === "register"
              ? `${role === "creator" ? "Creator" : "Verifier"} registration details ready for the account service.`
              : `${role === "creator" ? "Creator" : "Verifier"} login details ready for the account service.`,
          );
          navigate(mode === "register" ? "/signup" : "/login");
        }}
      >
        <input type="hidden" name="role" value={role} />
        {mode === "register" && (
          <>
            <label>
              <span>First Name</span>
              <input type="text" required autoComplete="given-name" placeholder="First name" />
            </label>
            <label>
              <span>Last Name <small>(optional)</small></span>
              <input type="text" autoComplete="family-name" placeholder="Last name" />
            </label>
          </>
        )}
        <label>
          <span>Email</span>
          <input type="email" required autoComplete="email" placeholder="you@example.com" />
        </label>
        <label>
          <span>Password</span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            placeholder="••••••••"
          />
        </label>
        <button className="button lime" type="submit">
          {mode === "register" ? "Create Account" : "Login"}
        </button>
      </form>
      {message && <p className="account-message" role="status">{message}</p>}
      <div className="account-switch">
        {mode === "register" ? (
          <>
            <span>Already have an account?</span>
            <button type="button" onClick={() => onSwitch("login")}>
              Existing User Login
            </button>
          </>
        ) : (
          <>
            <span>New here?</span>
            <button type="button" onClick={() => onSwitch("register")}>
              Register
            </button>
          </>
        )}
      </div>
    </>
  );
}

function AuthModal({
  mode,
  onSwitch,
  onClose,
}: {
  mode: "register" | "login" | null;
  onSwitch: (mode: "register" | "login") => void;
  onClose: () => void;
}) {
  if (!mode) return null;

  return (
    <div
      className="auth-modal-backdrop is-open"
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <section
        className="auth-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="auth-modal-close" type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
        <div id="auth-modal-title">
          <AccountAccess mode={mode} onSwitch={onSwitch} />
        </div>
      </section>
    </div>
  );
}

function LegalModal({
  kind,
  onClose,
}: {
  kind: "terms" | "privacy";
  onClose: () => void;
}) {
  const isTerms = kind === "terms";

  return (
    <div
      className="auth-modal-backdrop is-open"
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <section
        className="auth-modal legal-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="legal-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="auth-modal-close" type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
        <div className="legal-modal-body">
          <span className="section-mark">AUTHENTIQ / {isTerms ? "TERMS" : "PRIVACY"}</span>
          <h2 id="legal-modal-title">{isTerms ? "TERMS OF USE." : "PRIVACY POLICY."}</h2>
          {isTerms ? (
            <>
              <p>
                AUTHENTIQ provides tools for registering digital ownership records and generating
                cryptographic verification proofs. These terms describe responsible use of the
                service.
              </p>
              <h3>Using the service</h3>
              <p>
                You are responsible for the content you register, the accuracy of information you
                provide and keeping your account credentials secure. Do not register work you do
                not have the right to submit or use the service to make deceptive ownership claims.
              </p>
              <h3>Records and verification</h3>
              <p>
                A fingerprint, timestamp or proof can support an ownership claim but does not by
                itself settle every legal dispute or establish authorship in every jurisdiction.
                Verification results depend on the information and services available at the time.
              </p>
              <h3>Limitations</h3>
              <p>
                AUTHENTIQ is provided as an evolving software service. Availability, integrations
                and results may change, and the service is not legal advice or a substitute for
                independent evidence and professional counsel.
              </p>
            </>
          ) : (
            <>
              <p>
                AUTHENTIQ is designed to keep original digital works private while using
                fingerprints and cryptographic proof data for ownership workflows.
              </p>
              <h3>Information we use</h3>
              <p>
                Account details, role selections and service activity may be used to provide
                registration and verification features. The original work should remain local
                unless an explicitly connected backend workflow says otherwise.
              </p>
              <h3>Privacy choices</h3>
              <p>
                Do not submit information you do not want processed. Review connected service
                settings and backend documentation for retention, access and deletion controls.
                AUTHENTIQ does not promise that any system is completely secure or uninterrupted.
              </p>
              <h3>Updates</h3>
              <p>
                This policy may be updated as the product and integrations evolve. Continued use
                after an update means you have reviewed the revised policy.
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

type WorkspaceRole = "creator" | "verifier";
type CreatorView = "works" | "register" | "sharing";
type VerificationState = "idle" | "processing" | "success" | "failure" | "conflict";

const sampleWorks = [
  {
    name: "Sample research paper.pdf",
    fingerprint: "a3f7c2…9d1e4b",
    timestamp: "2026-01-15T10:32:00Z",
    status: "Sample record",
  },
  {
    name: "Sample identity mark.svg",
    fingerprint: "7b91e0…44af20",
    timestamp: "2025-12-04T08:18:42Z",
    status: "Sample record",
  },
];

function WorkspaceDashboard() {
  const [role, setRole] = useState<WorkspaceRole>("creator");
  const [creatorView, setCreatorView] = useState<CreatorView>("works");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fingerprint, setFingerprint] = useState("");
  const [hashState, setHashState] = useState<"idle" | "processing" | "ready" | "error">("idle");
  const [proofState, setProofState] = useState<"idle" | "processing" | "ready">("idle");
  const [shareState, setShareState] = useState<"idle" | "ready">("idle");
  const [verificationState, setVerificationState] = useState<VerificationState>("idle");
  const [verificationMessage, setVerificationMessage] = useState("");
  const [verifyFingerprint, setVerifyFingerprint] = useState("");
  const [verifyProof, setVerifyProof] = useState("");

  const hashFile = async (file: File) => {
    setSelectedFile(file);
    setFingerprint("");
    setHashState("processing");
    try {
      const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
      const value = Array.from(new Uint8Array(digest))
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");
      setFingerprint(value);
      setHashState("ready");
    } catch {
      setHashState("error");
    }
  };

  const generateProof = () => {
    setProofState("processing");
    window.setTimeout(() => setProofState("ready"), 500);
  };

  const downloadSharePackage = () => {
    if (!fingerprint) return;
    const packageData = {
      type: "AUTHENTIQ proof package",
      sample: true,
      filename: selectedFile?.name ?? "registered-work",
      sha256: fingerprint,
      proofCommitment: "Pending backend proof generation",
      originalFileIncluded: false,
    };
    const blob = new Blob([JSON.stringify(packageData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "authentiq-proof-package.json";
    link.click();
    URL.revokeObjectURL(url);
    setShareState("ready");
  };

  const verifyOwnership = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setVerificationState("processing");
    setVerificationMessage("");
    window.setTimeout(() => {
      setVerificationState("failure");
      setVerificationMessage(
        "Verification is not connected to the backend yet. No ownership result was fabricated.",
      );
    }, 500);
  };

  return (
    <div className="workspace-dashboard">
      <div className="workspace-role-switch" role="tablist" aria-label="Workspace role">
        {(["creator", "verifier"] as WorkspaceRole[]).map((workspaceRole) => (
          <button
            type="button"
            role="tab"
            aria-selected={role === workspaceRole}
            className={role === workspaceRole ? "active" : ""}
            onClick={() => setRole(workspaceRole)}
            key={workspaceRole}
          >
            {workspaceRole} workspace
          </button>
        ))}
      </div>

      {role === "creator" ? (
        <div className="dashboard-panel" key="creator">
          <div className="dashboard-tabs" role="tablist" aria-label="Creator workspace views">
            {([
              ["works", "Registered works"],
              ["register", "Register a work"],
              ["sharing", "Proof sharing"],
            ] as [CreatorView, string][]).map(([view, label]) => (
              <button
                type="button"
                role="tab"
                aria-selected={creatorView === view}
                className={creatorView === view ? "active" : ""}
                onClick={() => setCreatorView(view)}
                key={view}
              >
                {label}
              </button>
            ))}
          </div>

          {creatorView === "works" && (
            <div className="dashboard-content">
              <div className="dashboard-heading">
                <div>
                  <span className="section-mark">Creator workspace / registration history</span>
                  <h3>Registered works</h3>
                </div>
                <button className="button lime" type="button" onClick={() => setCreatorView("register")}>
                  Register work <Arrow />
                </button>
              </div>
              <div className="work-list">
                {sampleWorks.map((work) => (
                  <article className="work-record" key={work.name}>
                    <div>
                      <strong>{work.name}</strong>
                      <span>{work.status} · {work.timestamp}</span>
                    </div>
                    <code>{work.fingerprint}</code>
                  </article>
                ))}
              </div>
              <p className="dashboard-note">Sample records are clearly labelled and will be replaced by backend data.</p>
            </div>
          )}

          {creatorView === "register" && (
            <form className="dashboard-content dashboard-form" onSubmit={(event) => event.preventDefault()}>
              <div className="dashboard-heading">
                <div>
                  <span className="section-mark">Creator workspace / local fingerprinting</span>
                  <h3>Register a work</h3>
                </div>
                <span className={`state-pill ${hashState}`}>{hashState}</span>
              </div>
              <label className="file-drop">
                <span>Select a file to compute its SHA-256 fingerprint locally.</span>
                <input
                  type="file"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void hashFile(file);
                  }}
                />
                <strong>{selectedFile ? selectedFile.name : "Choose file"}</strong>
              </label>
              <div className="fingerprint-output">
                <span>SHA-256 fingerprint</span>
                <code>{fingerprint || "Waiting for a local file"}</code>
              </div>
              <div className="dashboard-actions">
                <button
                  className="button lime"
                  type="button"
                  disabled={!fingerprint || proofState === "processing"}
                  onClick={generateProof}
                >
                  {proofState === "processing" ? "Generating…" : "Generate ownership proof"}
                </button>
                {proofState === "ready" && (
                  <span className="state-message">Proof generation requires the backend service.</span>
                )}
              </div>
              <p className="dashboard-note">The original file remains in your browser and is not uploaded by this frontend.</p>
            </form>
          )}

          {creatorView === "sharing" && (
            <div className="dashboard-content">
              <div className="dashboard-heading">
                <div>
                  <span className="section-mark">Creator workspace / privacy-preserving sharing</span>
                  <h3>Proof packages</h3>
                </div>
              </div>
              <div className="share-card">
                <strong>Share without sharing the original</strong>
                <p>Generate a metadata package containing a fingerprint and proof placeholder. Original files are never included.</p>
                <button className="button dark" type="button" disabled={!fingerprint} onClick={downloadSharePackage}>
                  Download proof package <Arrow />
                </button>
                {shareState === "ready" && <span className="state-message">Package downloaded for sharing.</span>}
              </div>
              {!fingerprint && <p className="dashboard-note">Compute a fingerprint in Register a work before creating a package.</p>}
            </div>
          )}
        </div>
      ) : (
        <div className="dashboard-panel" key="verifier">
          <form className="dashboard-content dashboard-form" onSubmit={verifyOwnership}>
            <div className="dashboard-heading">
              <div>
                <span className="section-mark">Verifier workspace / proof validation</span>
                <h3>Verify ownership</h3>
              </div>
              <span className={`state-pill ${verificationState}`}>{verificationState}</span>
            </div>
            <label>
              <span>SHA-256 fingerprint</span>
              <input
                value={verifyFingerprint}
                onChange={(event) => setVerifyFingerprint(event.target.value)}
                placeholder="Paste fingerprint"
                required
              />
            </label>
            <label>
              <span>Proof commitment</span>
              <input
                value={verifyProof}
                onChange={(event) => setVerifyProof(event.target.value)}
                placeholder="Paste proof commitment"
                required
              />
            </label>
            <button className="button lime" type="submit" disabled={verificationState === "processing"}>
              {verificationState === "processing" ? "Checking ledger…" : "Verify ownership"} <Arrow />
            </button>
            {verificationState !== "idle" && verificationState !== "processing" && (
              <div className={`verification-result ${verificationState}`} role="status">
                <strong>
                  {verificationState === "success"
                    ? "Ownership verified"
                    : verificationState === "conflict"
                      ? "Claim conflict"
                      : "Verification unavailable"}
                </strong>
                <p>{verificationMessage}</p>
              </div>
            )}
            <p className="dashboard-note">Backend validation is required for success, failure, and conflict results. This interface never fabricates a cryptographic result.</p>
          </form>
        </div>
      )}
    </div>
  );
}

function App() {
  const navigate = useNavigate();
  const [isLoaded, setIsLoaded] = useState(false);
  const [openFaq, setOpenFaq] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [authModal, setAuthModal] = useState<"register" | "login" | null>(null);
  const [isAuthClosing, setIsAuthClosing] = useState(false);
  const [legalModal, setLegalModal] = useState<"terms" | "privacy" | null>(null);
  const [isLegalClosing, setIsLegalClosing] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  const scrollToSection = (sectionId: string, smooth = true) => {
    const section = document.getElementById(sectionId);
    if (!section) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    section.scrollIntoView({
      behavior: smooth && !reducedMotion ? "smooth" : "auto",
      block: "start",
    });
  };

  const navigateToSection = (sectionId: string) => {
    const nextHash = `#${sectionId}`;
    if (window.location.hash !== nextHash) {
      window.history.pushState({ sectionId }, "", nextHash);
    }
    setMenuOpen(false);
    scrollToSection(sectionId);
  };

  useEffect(() => {
    const handleHistoryNavigation = () => {
      const sectionId = window.location.hash.slice(1) || "overview";
      scrollToSection(sectionId);
      setMenuOpen(false);
    };
    window.addEventListener("popstate", handleHistoryNavigation);
    const initialHash = window.location.hash.slice(1);
    if (initialHash) scrollToSection(initialHash, true);
    return () => window.removeEventListener("popstate", handleHistoryNavigation);
  }, []);

  useEffect(() => {
    if (!authModal && !legalModal) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (authModal) closeAuthModal();
      else closeLegalModal();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [authModal, legalModal]);

  const openAuthModal = (mode: "register" | "login") => {
    setIsAuthClosing(false);
    setAuthModal(mode);
  };

  const closeAuthModal = () => {
    if (!authModal || isAuthClosing) return;
    setIsAuthClosing(true);
    window.setTimeout(() => {
      setAuthModal(null);
      setIsAuthClosing(false);
    }, 220);
  };

  const openLegalModal = (kind: "terms" | "privacy") => {
    setIsLegalClosing(false);
    setLegalModal(kind);
  };

  const closeLegalModal = () => {
    if (!legalModal || isLegalClosing) return;
    setIsLegalClosing(true);
    window.setTimeout(() => {
      setLegalModal(null);
      setIsLegalClosing(false);
    }, 220);
  };

  return (
    <>
      <LiquidCursor />
      <main className={isLoaded ? "site-shell is-loaded" : "site-shell"} aria-busy={!isLoaded}>
        <section className="hero" id="overview">
          <nav className="nav" aria-label="Main navigation">
            <button
              className="menu-toggle"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen}
              aria-label="Toggle navigation"
            >
              {menuOpen ? "CLOSE" : "MENU"}
            </button>
            <button className="brand" type="button" onClick={() => navigateToSection("overview")}>
              <img src="/favicon.png" alt="AUTHENTIQ" />
            </button>
            <div className={`nav-links ${menuOpen ? "open" : ""}`}>
              <button type="button" onClick={() => navigateToSection("verifier")}>
                Workspace
              </button>
              <button type="button" onClick={() => navigateToSection("how-it-works")}>
                Working
              </button>
              <button type="button" onClick={() => navigateToSection("detection")}>
                Technology
              </button>
              <button type="button" onClick={() => navigateToSection("applications")}>
                Applications
              </button>
              <button type="button" onClick={() => navigateToSection("faq")}>
                FAQ
              </button>
              <button type="button" onClick={() => navigateToSection("contact")}>
                Contact
              </button>
              <button type="button" onClick={() => navigate("/verify")}>
                Verify
              </button>
              <button type="button" onClick={() => navigate("/records")}>
                Records
              </button>
            </div>
          </nav>

          <div className="hero-content page-pad">
            <HeroNetwork />
            <h1 className="hero-title">
              <div>AUTHENTIQ</div>
            </h1>
            <div className="hero-bottom">
              <div className="hero-kicker">
                PROVE WHAT'S YOURS.
                <br />
                KEEP IT PRIVATE.
              </div>
              <p>
                Register your digital creations on an immutable ledger. Prove ownership through
                cryptographic verification without revealing the original work.
              </p>
              <div className="button-row">
                <button
                  className="button lime"
                  type="button"
                  onClick={() => openAuthModal("register")}
                >
                  GET STARTED <Arrow />
                </button>
                <button className="button dark" type="button" onClick={() => navigate("/verify")}>
                  VERIFY OWNERSHIP <Arrow />
                </button>
              </div>
            </div>
          </div>
          <div className="hero-meta page-pad">
            <div className="mini-ledger">
              <i></i>
              <i></i>
              <i className="hot"></i>
              <i></i>
            </div>
          </div>
        </section>

        <div className="ticker" aria-label="Product capabilities">
          <div className="ticker-track">
            {[
              ...[
                "DIGITAL OWNERSHIP",
                "SHA-256 FINGERPRINTING",
                "ZERO-KNOWLEDGE PROOFS",
                "BLOCKCHAIN TIMESTAMPS",
                "PRIVACY-PRESERVING",
                "CREATOR VERIFICATION",
                "DISPUTE RESOLUTION",
              ],
              ...[
                "DIGITAL OWNERSHIP",
                "SHA-256 FINGERPRINTING",
                "ZERO-KNOWLEDGE PROOFS",
                "BLOCKCHAIN TIMESTAMPS",
                "PRIVACY-PRESERVING",
                "CREATOR VERIFICATION",
                "DISPUTE RESOLUTION",
              ],
            ].map((item, i) => (
              <span key={`${item}-${i}`} className={i % 2 ? "outline" : ""}>
                {item}
                <b>✳</b>
              </span>
            ))}
          </div>
        </div>

        <section className="verify section-pad" id="verify">
          <div className="section-heading">
            <div className="section-mark">How digital ownership works</div>
            <h2>
              PROVE
              <br />
              <span>✦</span> OWNERSHIP
            </h2>
          </div>
          <div className="verify-copy">
            <p className="lead">
              Digital works are registered as SHA-256 fingerprints on an immutable blockchain
              ledger. Ownership is proven through Zero-Knowledge Proofs, allowing you to verify
              authenticity without ever revealing the original file.
              <br />
              <br />
              Your file stays private. Only its fingerprint is recorded.
            </p>
            <div className="tags">
              {[
                "Digital Fingerprints",
                "Zero-Knowledge Proofs",
                "Blockchain Ledger",
                "Privacy-Preserving",
                "Ownership Verification",
              ].map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          </div>
          <div className="stats-grid">
            {[
              ["SHA-256", "Cryptographic fingerprint", "Per file"],
              ["ZERO", "Original files stored", "On-chain or off-chain"],
              ["ZKP", "Proof generation", "Circom / snarkjs"],
              ["IMMUTABLE", "Ledger timestamps", "Tamper-evident"],
            ].map(([value, label, note]) => (
              <article className="stat-pill" key={value}>
                <strong>{value}</strong>
                <span>{label}</span>
                <small>{note}</small>
              </article>
            ))}
          </div>
          <p className="benchmark-note">
            The verification flow is illustrative. Actual SHA-256, ZKP and blockchain operations are
            handled by the backend modules.
          </p>
        </section>

        <section className="immutability section-pad">
          <div className="immutability-copy">
            <span className="section-mark">Why privacy matters</span>
            <h2>
              YOUR FILE STAYS
              <br />
              PRIVATE.
            </h2>
            <p>
              AUTHENTIQ never stores or transmits your original work. Only its SHA-256 fingerprint
              and a Zero-Knowledge Proof commitment are registered on the ledger.
            </p>
          </div>
          <div className="truth-sequence" aria-label="Digital ownership verification sequence">
            {["FINGERPRINT", "PROOF COMMITMENT", "LEDGER REGISTRATION"].map((item, index) => (
              <div className="truth-node" key={item}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{item}</strong>
                {index < 2 && <Arrow />}
              </div>
            ))}
            <div className="verification-layer">
              <span>PRIVACY-PRESERVING VERIFICATION</span>
              <strong>AUTHENTIQ</strong>
              <p>Zero-Knowledge Proofs verify ownership without revealing the work.</p>
            </div>
          </div>
        </section>

        <section className="detection section-pad" id="detection">
          <div className="section-title-line">
            <h2>
              CORE <span>✳</span> TECHNOLOGY
            </h2>
            <p>Four focused capabilities. One verification layer.</p>
          </div>
          <div className="detection-grid">
            {detectionCards.map((card) => (
              <DetectionCard card={card} key={card.number} />
            ))}
          </div>
        </section>

        <section className="workflow section-pad" id="how-it-works">
          <div className="workflow-head">
            <span className="section-mark">How digital ownership works</span>
            <h2>
              <span>✦</span> PROVE
              <br />
              OWNERSHIP
            </h2>
            <div className="round-mark">✦</div>
          </div>
          <div className="steps">
            {[
              [
                "01",
                "Register",
                "Upload a digital work. Its SHA-256 fingerprint is computed locally.",
              ],
              [
                "02",
                "Fingerprint",
                "The fingerprint is registered with a timestamp on the blockchain ledger.",
              ],
              [
                "03",
                "Generate Proof",
                "A Zero-Knowledge Proof commitment is created without exposing the file.",
              ],
              [
                "04",
                "Verify",
                "Ownership is proven by validating the proof against the registered fingerprint.",
              ],
            ].map(([n, title, text]) => (
              <article className="step" key={n}>
                <span>{n}</span>
                <div className="step-node"></div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="report section-pad">
          <div className="report-title">
            <span className="section-mark">Sample verification report</span>
            <h2>
              WHAT A
              <br />
              VERIFICATION REPORT
              <span>✦</span> LOOKS LIKE
            </h2>
          </div>
          <div className="report-layout">
            <article className="main-report">
              <header>
                <span>SAMPLE VERIFICATION REPORT / ILLUSTRATIVE DATA</span>
                <span className="status">OWNER VERIFIED</span>
              </header>
              <div className="report-id">
                <span>FILE FINGERPRINT</span>
                <strong>a3f7c2…9d1e4b</strong>
                <i>TX-01940</i>
              </div>
              <dl>
                <div>
                  <dt>Registration timestamp</dt>
                  <dd>2026-01-15T10:32:00Z</dd>
                </div>
                <div>
                  <dt>Proof commitment</dt>
                  <dd>zKP-commit-8e1b5a</dd>
                </div>
                <div>
                  <dt>Validation status</dt>
                  <dd>VALID</dd>
                </div>
                <div>
                  <dt>Ledger reference</dt>
                  <dd>0x7742…9021</dd>
                </div>
              </dl>
              <div className="evidence-list">
                <strong>SUPPORTING DOCUMENTS</strong>
                <span>Original artwork file</span>
                <span>Creation metadata</span>
                <span>Creator identity hash</span>
              </div>
            </article>
            <div className="report-side">
              <p>
                This illustrative report confirms that the registered fingerprint matches the
                submitted proof. Sample data only — not a real blockchain transaction.
              </p>
              <article className="mini-report">
                <span>ILLUSTRATIVE / OWNER VERIFIED</span>
                <b>OWNER VERIFIED</b>
                <h3>DIGITAL OWNERSHIP CONFIRMED</h3>
                <div>
                  <strong>SHA-256</strong>
                  <small>Fingerprint match</small>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="verify section-pad" id="verifier">
          <div className="section-heading">
            <div className="section-mark">Workspace</div>
            <h2>WORKSPACE</h2>
          </div>
          <WorkspaceDashboard />
        </section>

        <section className="report section-pad" id="dispute">
          <div className="report-title">
            <span className="section-mark">Dispute resolution</span>
            <h2>
              CONFLICTING
              <br />
              <span>✦</span> CLAIMS
            </h2>
          </div>
          <div className="report-layout">
            <article className="main-report">
              <header>
                <span>DISPUTE RESOLUTION / ILLUSTRATIVE DATA</span>
                <span className="status">CLAIM RESOLVED</span>
              </header>
              <div className="report-id">
                <span>DISPUTE ID</span>
                <strong>DSP-00482</strong>
                <i>RESOLVED</i>
              </div>
              <dl>
                <div>
                  <dt>Claim A fingerprint</dt>
                  <dd>a3f7c2…9d1e4b</dd>
                </div>
                <div>
                  <dt>Claim A timestamp</dt>
                  <dd>2026-01-15T10:32:00Z</dd>
                </div>
                <div>
                  <dt>Claim B fingerprint</dt>
                  <dd>a3f7c2…9d1e4b</dd>
                </div>
                <div>
                  <dt>Claim B timestamp</dt>
                  <dd>2026-01-15T11:45:00Z</dd>
                </div>
              </dl>
              <div className="evidence-list">
                <strong>RESOLUTION BASIS</strong>
                <span>Earliest valid timestamp</span>
                <span>Proof commitment match</span>
                <span>Ledger immutability</span>
              </div>
            </article>
            <div className="report-side">
              <p>
                When two parties claim the same work, the earliest valid ledger timestamp determines
                ownership. Sample data only — not a real dispute resolution.
              </p>
              <article className="mini-report">
                <span>ILLUSTRATIVE / CLAIM RESOLVED</span>
                <b>CLAIM A WINS</b>
                <h3>EARLIER TIMESTAMP PREVAILS</h3>
                <div>
                  <strong>CLAIM A</strong>
                  <small>10:32:00Z</small>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="applications section-pad" id="applications">
          <div className="section-title-line">
            <h2>
              APPLICATION <span>✳</span> AREAS
            </h2>
            <p>Supported digital work types.</p>
          </div>
          <div className="application-grid">
            {applications.map((app, i) => (
              <article key={app.title}>
                <div className={`application-visual ${app.type}`}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <i></i>
                  <i></i>
                  <i></i>
                </div>
                <h3>{app.title}</h3>
                <ul>
                  {app.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="faq section-pad" id="faq">
          <div className="faq-title">
            <h2>FAQ</h2>
            <span>✳</span>
          </div>
          <div className="faq-list">
            {faqs.map((faq, i) => {
              const open = openFaq === i;
              return (
                <article className={open ? "faq-item open" : "faq-item"} key={faq.q}>
                  <button onClick={() => setOpenFaq(open ? -1 : i)} aria-expanded={open}>
                    <span>{faq.q}</span>
                    <i>{open ? "−" : "+"}</i>
                  </button>
                  <div className="faq-answer">
                    <p>{faq.a}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <footer id="contact">
          <div className="footer-main">
            <div className="footer-brand">AUTHENTIQ</div>
            <div className="footer-team">
              <span>TEAM FANTASTIC FOUR</span>
              <div>
                {[
                  "Mohit Nagdeep",
                  "Rakshak Patel V",
                  "Sampath Nagaraj Shet",
                  "Sushanth Sapare",
                ].map((name) => (
                  <a
                    href="#contact"
                    key={name}
                    onClick={(event) => {
                      event.preventDefault();
                      navigateToSection("contact");
                    }}
                  >
                    {name} <Arrow diagonal />
                  </a>
                ))}
              </div>
            </div>
            <div className="footer-rings" aria-hidden="true"></div>
            <div className="footer-legal">
              <button type="button" onClick={() => openLegalModal("terms")}>
                Terms of Use
              </button>
              <button type="button" onClick={() => openLegalModal("privacy")}>
                Privacy Policy
              </button>
            </div>
            <div className="footer-copyright">© 2026 AUTHENTIQ</div>
          </div>
        </footer>
      </main>
      {authModal && (
        <div className={isAuthClosing ? "auth-modal-layer is-closing" : "auth-modal-layer"}>
          <AuthModal
            mode={authModal}
            onSwitch={openAuthModal}
            onClose={closeAuthModal}
          />
        </div>
      )}
      {legalModal && (
        <div className={isLegalClosing ? "auth-modal-layer is-closing" : "auth-modal-layer"}>
          <LegalModal kind={legalModal} onClose={closeLegalModal} />
        </div>
      )}
    </>
  );
}

export default App;
