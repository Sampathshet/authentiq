import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  BookOpen,
  Building2,
  Boxes,
  ChevronDown,
  CircleHelp,
  FolderLock,
  Gauge,
  Globe,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Menu,
  PlusCircle,
  Search,
  Settings,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Users,
  ArrowLeftRight,
  Gavel,
  ScrollText,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { LedgerStatus, NotificationItem, Paginated } from "@/lib/types";
import { initials, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import { BrandLogo } from "@/components/BrandLogo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const navSections: Array<{
  label: string;
  roles?: string[];
  items: Array<{ to: string; label: string; icon: LucideIcon }>;
}> = [
  {
    label: "Workspace",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/register", label: "Register creation", icon: PlusCircle },
      { to: "/timeline", label: "Creative timeline", icon: Activity },
      { to: "/ideas", label: "Idea vault", icon: Lightbulb },
      { to: "/provenance", label: "AI provenance", icon: Sparkles },
    ],
  },
  {
    label: "Collaboration",
    items: [
      { to: "/teams", label: "Teams", icon: Users },
      { to: "/organization", label: "Organization", icon: Building2 },
      { to: "/transfers", label: "Transfers", icon: ArrowLeftRight },
      { to: "/disputes", label: "Disputes", icon: Gavel },
    ],
  },
  {
    label: "Trust center",
    items: [
      { to: "/anonymous-verification", label: "Prove ownership", icon: ShieldCheck },
      { to: "/verify", label: "Public verifier", icon: Globe },
      { to: "/records", label: "Public records", icon: BookOpen },
      { to: "/integrity", label: "Integrity center", icon: Gauge },
      { to: "/alerts", label: "Alerts", icon: Boxes },
      { to: "/audit-logs", label: "Ledger & audit", icon: ScrollText },
      { to: "/notifications", label: "Notifications", icon: Bell },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
  {
    label: "Administration",
    roles: ["site_admin"],
    items: [
      { to: "/admin", label: "Site administration", icon: ShieldAlert },
    ],
  },
];

interface SearchResults {
  registrations: { id: string; registration_id: string; title: string; asset_type: string }[];
  ideas: { idea_ref: string; title: string }[];
  teams: { id: string; name: string; status: string }[];
  disputes: { dispute_ref: string; reason: string; status: string }[];
  alerts: { id: string; type: string; status: string }[];
  total: number;
}

function Brand({ compact }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <BrandLogo className="size-9 rounded-xl shadow-[0_10px_30px_-12px_rgba(99,102,241,0.9)] ring-1 ring-white/10" />
      {!compact && (
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-[0.2em]">AUTHENTIQ</p>
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Ownership infrastructure</p>
        </div>
      )}
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const visibleSections = navSections.filter(
    (section) => !section.roles || section.roles.includes(user?.role || ""),
  );
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center border-b border-border/60 px-5">
        <Brand />
      </div>
      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {visibleSections.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground/70">{section.label}</p>
            <nav className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-accent/15 text-muted-foreground shadow-[inset_0_0_0_1px_rgba(59,130,246,0.18)]"
                        : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                    )
                  }
                >
                  <item.icon className="size-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        ))}
      </div>
      <div className="border-t border-border/60 p-3">
        <div className="rounded-lg border border-border/60 bg-background/40 p-3">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-muted-foreground">
            <span className="size-1.5 rounded-full bg-emerald-400 pulse-dot" />
            LOCAL APPEND-ONLY LEDGER
          </div>
          <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground/80">
            Records are simulated locally. No public blockchain transaction is claimed.
          </p>
          <NavLink to="/audit-logs" onClick={onNavigate} className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-foreground hover:text-foreground">
            Inspect integrity <ChevronDown className="size-3 -rotate-90" />
          </NavLink>
        </div>
        {user?.is_demo && (
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-accent/40 bg-accent/15 px-3 py-2 text-[11px] text-foreground">
            <Sparkles className="size-3.5" />
            Demo workspace · no records yet
          </div>
        )}
      </div>
    </div>
  );
}

function NotificationMenu() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["notifications", "menu"],
    queryFn: () => api.get<Paginated<NotificationItem> & { unread: number }>("/notifications?page_size=6"),
    refetchInterval: 60000,
  });

  const markAll = async () => {
    await api.post("/notifications/read-all");
    toast.success("All notifications marked as read");
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4" />
          {(data?.unread || 0) > 0 && (
            <span className="absolute right-1.5 top-1.5 flex size-4 items-center justify-center rounded-full bg-foreground text-[9px] font-bold text-white">
              {data && data.unread > 9 ? "9+" : data?.unread}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-2 py-1.5">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {!!data?.unread && (
            <button type="button" onClick={markAll} className="text-[11px] font-medium text-foreground hover:text-foreground">
              Mark all read
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        {data?.items?.length ? (
          data.items.map((item) => (
            <DropdownMenuItem
              key={item.id}
              className="flex-col items-start gap-0.5 py-2.5"
              onClick={() => navigate("/notifications")}
            >
              <span className="flex w-full items-center gap-2">
                <span className={cn("size-1.5 shrink-0 rounded-full", item.is_read ? "bg-muted-foreground/40" : "bg-blue-400")} />
                <span className="truncate text-xs font-medium">{item.title}</span>
              </span>
              <span className="line-clamp-2 pl-3.5 text-[11px] text-muted-foreground">{item.message}</span>
              <span className="pl-3.5 text-[10px] text-muted-foreground/70">{relativeTime(item.created_at)}</span>
            </DropdownMenuItem>
          ))
        ) : (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground">No notifications yet</div>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate("/notifications")} className="justify-center text-xs text-foreground">
          Open notification center
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function GlobalSearch({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { data, isFetching } = useQuery({
    queryKey: ["global-search", query],
    queryFn: () => api.get<SearchResults>(`/search?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
  });

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const go = (path: string) => {
    onOpenChange(false);
    navigate(path);
  };

  const groups = [
    ...(data?.registrations || []).map((item) => ({
      key: `r-${item.id}`,
      label: item.title,
      meta: `${item.registration_id} · ${titleCase(item.asset_type)}`,
      path: `/registrations/${item.id}`,
    })),
    ...(data?.ideas || []).map((item) => ({
      key: `i-${item.idea_ref}`,
      label: item.title,
      meta: `Idea ${item.idea_ref}`,
      path: `/ideas/${item.idea_ref}`,
    })),
    ...(data?.teams || []).map((item) => ({
      key: `t-${item.id}`,
      label: item.name,
      meta: `Team · ${titleCase(item.status)}`,
      path: `/teams/${item.id}`,
    })),
    ...(data?.disputes || []).map((item) => ({
      key: `d-${item.dispute_ref}`,
      label: item.dispute_ref,
      meta: `${item.reason} · ${titleCase(item.status)}`,
      path: `/disputes/${item.dispute_ref}`,
    })),
    ...(data?.alerts || []).map((item) => ({
      key: `a-${item.id}`,
      label: item.type.replace(/_/g, " "),
      meta: `Alert · ${titleCase(item.status)}`,
      path: "/alerts",
    })),
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[18%] max-w-xl translate-y-0 gap-3 p-4">
        <DialogHeader className="sr-only">
          <DialogTitle>Search AUTHENTIQ</DialogTitle>
        </DialogHeader>
        <div className="flex items-center gap-2 border-b border-border/60 pb-3">
          <Search className="size-4 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search creations, ideas, teams, disputes..."
            className="h-9 border-0 bg-transparent px-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
            <X />
          </Button>
        </div>
        <div className="max-h-[46vh] overflow-y-auto">
          {query.trim().length < 2 && (
            <p className="px-2 py-8 text-center text-xs text-muted-foreground">
              Search uses the authenticated backend index. Type at least two characters.
            </p>
          )}
          {query.trim().length >= 2 && isFetching && <p className="px-2 py-8 text-center text-xs text-muted-foreground">Searching...</p>}
          {query.trim().length >= 2 && !isFetching && !groups.length && (
            <p className="px-2 py-8 text-center text-xs text-muted-foreground">No matching records in your workspace.</p>
          )}
          <div className="space-y-1">
            {groups.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => go(item.path)}
                className="flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent"
              >
                <span className="text-sm font-medium">{item.label}</span>
                <span className="text-[11px] text-muted-foreground">{item.meta}</span>
              </button>
            ))}
          </div>
        </div>
        <p className="border-t border-border/60 pt-2 text-[10px] text-muted-foreground">
          Results are limited to records your account is authorized to access.
        </p>
      </DialogContent>
    </Dialog>
  );
}

function LedgerChip() {
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["ledger-status"],
    queryFn: () => api.get<LedgerStatus>("/ledger/status"),
    refetchInterval: 60000,
    staleTime: 20000,
  });
  const simulated = !data || data.mode === "simulation";
  return (
    <button
      type="button"
      onClick={() => navigate("/audit-logs")}
      className="hidden items-center gap-2 rounded-full border border-border/70 bg-background/40 px-3 py-1.5 text-[11px] font-medium transition-colors hover:bg-accent lg:inline-flex"
      title={data?.message || data?.label}
    >
      <span className={cn("size-1.5 rounded-full", simulated ? "bg-amber-400" : "bg-violet-400")} />
      <span className="text-muted-foreground">{simulated ? "Simulated ledger" : "Polygon Amoy"}</span>
      <span className="text-muted-foreground/50">·</span>
      <span className="font-mono text-muted-foreground">{data?.block_number ? `block ${data.block_number}` : "not connected"}</span>
    </button>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className="flex items-center gap-2 rounded-full border border-border/60 bg-background/40 p-1 pr-2 transition-colors hover:bg-accent">
          <span
            className="flex size-7 items-center justify-center rounded-full text-[11px] font-bold text-white"
            style={{ backgroundColor: user.avatar_color || "#171717" }}
          >
            {initials(user.display_name)}
          </span>
          <span className="hidden max-w-[120px] truncate text-xs font-medium sm:block">{user.display_name}</span>
          <ChevronDown className="size-3 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>Signed in</DropdownMenuLabel>
        <div className="px-2.5 pb-2">
          <p className="truncate text-sm font-medium">{user.display_name}</p>
          <p className="truncate text-[11px] text-muted-foreground">{user.email}</p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            <Badge variant={user.role === "site_admin" ? "violet" : user.role === "verifier" ? "violet" : user.role === "org_admin" ? "blue" : "slate"}>{titleCase(user.role)}</Badge>
            {user.organization_name && <Badge variant="outline">{user.organization_name}</Badge>}
          </div>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => navigate("/settings")}>
            <Settings /> Account settings
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/organization")}>
            <Building2 /> Organization
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/notifications")}>
            <Bell /> Notifications
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/anonymous-verification")}>
            <CircleHelp /> Verification help
          </DropdownMenuItem>
          {user.role === "site_admin" && (
            <DropdownMenuItem onClick={() => navigate("/admin")}>
              <ShieldAlert /> Site administration
            </DropdownMenuItem>
          )}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => logout()} className="text-destructive focus:text-destructive">
          <LogOut /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  const crumbs = useMemo(() => {
    const segments = location.pathname.split("/").filter(Boolean);
    if (!segments.length) return [];
    return segments.map((segment) => {
      if (/^[0-9a-f-]{20,}$/i.test(segment)) return "Detail";
      return titleCase(decodeURIComponent(segment).replace(/-/g, " "));
    });
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background">
      <div className="pointer-events-none fixed inset-0 -z-10 grid-bg opacity-60" />
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[260px] border-r border-border/60 bg-card/50 backdrop-blur-xl lg:block">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="relative h-full w-[280px] border-r border-border bg-card shadow-2xl">
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4 z-10 rounded-md p-1.5 text-muted-foreground hover:bg-accent"
              aria-label="Close navigation"
            >
              <X className="size-4" />
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-[260px]">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border/60 bg-background/70 px-4 backdrop-blur-xl md:px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu />
          </Button>
          <div className="hidden min-w-0 items-center gap-2 text-xs text-muted-foreground sm:flex">
            {crumbs.map((crumb, index) => (
              <span key={`${crumb}-${index}`} className="flex items-center gap-2">
                {index > 0 && <span className="text-border">/</span>}
                <span className={index === crumbs.length - 1 ? "font-medium text-foreground" : ""}>{crumb}</span>
              </span>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex h-9 items-center gap-2 rounded-lg border border-border/70 bg-background/40 px-3 text-xs text-muted-foreground transition-colors hover:bg-accent md:w-56"
            >
              <Search className="size-3.5" />
              <span className="hidden md:inline">Search workspace</span>
              <kbd className="ml-auto hidden rounded border border-border/70 px-1.5 py-0.5 font-mono text-[10px] md:inline">⌘K</kbd>
            </button>
            <LedgerChip />
            <NotificationMenu />
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1500px] px-4 py-6 md:px-6 md:py-8">
          <Outlet />
        </main>
      </div>
      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </div>
  );
}
