import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, ShieldCheck, Fingerprint, KeyRound, Network } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { Button } from "@/components/ui/button";

const facts = [
  { icon: Fingerprint, title: "SHA-256 canonical fingerprints", text: "Hashed in your browser, verified chunk by chunk, and compared again on the server." },
  { icon: KeyRound, title: "Real commitment proofs", text: "Poseidon commitments and a BN254 Schnorr proof of knowledge. No simulated cryptography." },
  { icon: ShieldCheck, title: "Encrypted at rest", text: "Files and private idea content are encrypted. Every privileged action enters a hash-chained audit log." },
];

function NetworkCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let width = 0;
    let height = 0;

    const nodes = Array.from({ length: 30 }, () => ({
      x: Math.random(),
      y: Math.random(),
      vx: (Math.random() - 0.5) * 0.00045,
      vy: (Math.random() - 0.5) * 0.00045,
      r: 1 + Math.random() * 2.2,
      accent: Math.random() > 0.78,
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = () => {
      context.clearRect(0, 0, width, height);
      const scale = Math.min(width, height);
      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];
        if (!reduced) {
          node.x += node.vx;
          node.y += node.vy;
          if (node.x < 0 || node.x > 1) node.vx *= -1;
          if (node.y < 0 || node.y > 1) node.vy *= -1;
        }
        for (let j = i + 1; j < nodes.length; j += 1) {
          const other = nodes[j];
          const dx = (node.x - other.x) * width;
          const dy = (node.y - other.y) * height;
          const distance = Math.hypot(dx, dy);
          if (distance < scale * 0.22) {
            context.beginPath();
            context.strokeStyle = `rgba(23, 23, 23, ${0.16 * (1 - distance / (scale * 0.22))})`;
            context.lineWidth = 1;
            context.moveTo(node.x * width, node.y * height);
            context.lineTo(other.x * width, other.y * height);
            context.stroke();
          }
        }
      }
      for (const node of nodes) {
        const x = node.x * width;
        const y = node.y * height;
        const glow = context.createRadialGradient(x, y, 0, x, y, node.r * 8);
        const tint = node.accent ? "183, 255, 0" : "35, 31, 32";
        glow.addColorStop(0, `rgba(${tint}, 0.45)`);
        glow.addColorStop(1, `rgba(${tint}, 0)`);
        context.fillStyle = glow;
        context.beginPath();
        context.arc(x, y, node.r * 8, 0, Math.PI * 2);
        context.fill();
        context.fillStyle = node.accent ? "rgba(183, 255, 0, 0.95)" : "rgba(23, 23, 23, 0.85)";
        context.beginPath();
        context.arc(x, y, node.r, 0, Math.PI * 2);
        context.fill();
      }
      frame = window.requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener("resize", resize);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 size-full opacity-80" aria-hidden="true" />;
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 radial-glow opacity-70" />
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-40" />
      <div className="relative mx-auto grid min-h-screen max-w-[1400px] lg:grid-cols-[1.05fr_1fr]">
        <section className="relative hidden overflow-hidden border-r border-border/60 p-10 lg:flex lg:flex-col lg:justify-between xl:p-14">
          <NetworkCanvas />
          <div className="relative">
            <div className="flex items-center gap-3">
              <BrandLogo className="size-11 rounded-2xl shadow-[0_16px_40px_-16px_rgba(23,23,23,0.85)] ring-1 ring-white/10" />
              <div>
                <p className="text-base font-semibold tracking-[0.24em]">AUTHENTIQ</p>
                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Digital ownership infrastructure</p>
              </div>
            </div>
          </div>
          <div className="relative max-w-xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-foreground/20 bg-accent/15 px-3 py-1 text-[11px] font-medium text-foreground">
              <Network className="size-3.5" />
              Cryptographic provenance, not marketing copy
            </p>
            <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight xl:text-5xl">
              Protect the creation.
              <br />
              <span className="text-gradient">Prove the ownership.</span>
              <br />
              Preserve the privacy.
            </h1>
            <p className="mt-5 max-w-lg text-sm leading-relaxed text-muted-foreground">
              A complete workspace for creators, teams, and organizations: register creative work, protect unrevealed ideas, run real
              zero-knowledge ownership proofs, and resolve disputes with an append-only evidence trail.
            </p>
            <div className="mt-8 space-y-4">
              {facts.map((fact) => (
                <div key={fact.title} className="flex gap-3">
                  <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-card/70 text-foreground">
                    <fact.icon className="size-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{fact.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{fact.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="relative flex items-center gap-6 text-[11px] text-muted-foreground">
            <span>Argon2id password hashing</span>
            <span className="size-1 rounded-full bg-border" />
            <span>Append-only audit chain</span>
            <span className="size-1 rounded-full bg-border" />
            <span>AES-256-GCM storage</span>
          </div>
        </section>
        <section className="flex min-h-screen items-center justify-center p-5 sm:p-8">
          <div className="w-full max-w-md">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
              <Link
                to="/"
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                <ArrowLeft className="size-3.5" /> Back to home
              </Link>
              <Button asChild size="sm" variant="outline">
                <Link to="/verify">
                  <ShieldCheck className="size-3.5" /> Public verification <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
            {children}
          </div>
        </section>
      </div>
    </div>
  );
}
