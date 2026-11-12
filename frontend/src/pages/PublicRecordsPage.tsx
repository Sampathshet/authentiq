import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Fingerprint,
  Globe,
  Layers,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { CopyButton, HashValue } from "@/components/common/hash-value";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatDate, initials, relativeTime, titleCase } from "@/lib/format";

interface PublicRecordItem {
  registration_reference: string;
  title: string;
  description?: string | null;
  description_truncated?: boolean;
  creator_name: string;
  organization?: string | null;
  team_name?: string | null;
  asset_type: string;
  tags: string[];
  fingerprint: string;
  commitment?: string | null;
  status: string;
  verified_at?: string | null;
  registered_at: string;
  creation_timestamp?: string | null;
  ledger_mode?: string | null;
  ledger_tx_id?: string | null;
  verify_path: string;
}

interface PublicRecordsResponse {
  items: PublicRecordItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  query?: string | null;
  sort: string;
  asset_type?: string | null;
  total_creators: number;
  latest_registered_at?: string | null;
  asset_types: { value: string; count: number }[];
  privacy_note: string;
}

const PAGE_SIZE = 9;

function buildParams(query: string, assetType: string, sort: string, page: number) {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), sort });
  if (query) params.set("q", query);
  if (assetType) params.set("asset_type", assetType);
  return params.toString();
}

function StatTile({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card/70 p-4">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        <span className="flex size-6 items-center justify-center rounded-md bg-foreground/10 text-foreground">
          {icon}
        </span>
        {label}
      </div>
      <p className="mt-2 text-xl font-semibold tracking-tight text-foreground">{value}</p>
      {hint ? <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function RecordCard({ record }: { record: PublicRecordItem }) {
  const verified = record.status === "verified";
  return (
    <article className="flex h-full flex-col gap-3.5 rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-foreground/10 text-[11px] font-semibold text-foreground">
            {initials(record.creator_name)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{record.creator_name}</p>
            <p className="truncate text-[11px] text-muted-foreground">
              {record.team_name ? `Team: ${record.team_name}` : record.organization || "Independent creator"}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Badge variant={verified ? "green" : "slate"}>{verified ? "Verified" : "Registered"}</Badge>
          <Badge variant="outline">{titleCase(record.asset_type)}</Badge>
        </div>
      </div>

      <div>
        <h3 className="text-[15px] font-semibold leading-snug text-foreground">{record.title}</h3>
        {record.team_name ? (
          <p className="mt-1 text-[11px] font-medium text-foreground">
            Created by {record.creator_name} for team {record.team_name}
          </p>
        ) : null}
        {record.description ? (
          <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
            {record.description}
            {record.description_truncated ? "…" : ""}
          </p>
        ) : null}
      </div>

      {record.tags.length ? (
        <div className="flex flex-wrap gap-1.5">
          {record.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="rounded-md border border-border/70 px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <dl className="mt-auto space-y-1.5 border-t border-border/60 pt-3 text-[11px]">
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">Reference</dt>
          <dd className="flex items-center gap-1.5">
            <code className="truncate font-mono text-foreground">{record.registration_reference}</code>
            <CopyButton value={record.registration_reference} label="Registration reference" />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">SHA-256</dt>
          <dd>
            <HashValue value={record.fingerprint} label="Public fingerprint" head={10} tail={8} />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted-foreground">Registered</dt>
          <dd className="text-foreground">{formatDate(record.registered_at)}</dd>
        </div>
      </dl>

      <div className="flex items-center justify-between gap-2 pt-1">
        <span className="text-[10px] text-muted-foreground">
          {record.ledger_tx_id ? `Ledger ${record.ledger_mode || "simulation"}` : "Not anchored to a ledger"}
        </span>
        <Button asChild variant="outline" size="sm" className="border-border bg-transparent hover:bg-accent">
          <Link to={record.verify_path}>
            Open record <ArrowRight />
          </Link>
        </Button>
      </div>
    </article>
  );
}

export default function PublicRecordsPage() {
  const [rawQuery, setRawQuery] = useState("");
  const [query, setQuery] = useState("");
  const [assetType, setAssetType] = useState("");
  const [sort, setSort] = useState("recent");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(rawQuery.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [rawQuery]);

  const recordsQuery = useQuery({
    queryKey: ["public-records", query, assetType, sort, page],
    queryFn: () =>
      api.publicGet<PublicRecordsResponse>(
        `/public/records?${buildParams(query, assetType, sort, page)}`,
      ),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const data = recordsQuery.data;
  const items = data?.items ?? [];
  const pages = data?.pages ?? 0;

  const pageNumbers = useMemo(() => {
    if (pages <= 1) return [1];
    const windowStart = Math.max(1, Math.min(page - 2, pages - 4));
    const windowEnd = Math.min(pages, windowStart + 4);
    return Array.from({ length: windowEnd - windowStart + 1 }, (_, index) => windowStart + index);
  }, [page, pages]);

  const isInitialLoading = recordsQuery.isLoading;
  const hasFilters = Boolean(query || assetType);

  return (
    <div className="relative min-h-screen overflow-hidden bg-foreground text-foreground">
      <div className="pointer-events-none absolute inset-0 -z-0 grid-bg opacity-40" />
      <div className="pointer-events-none absolute -left-24 top-0 -z-0 size-[420px] rounded-full bg-blue-600/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 -z-0 size-[420px] rounded-full bg-violet-600/15 blur-3xl" />

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-8 md:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5">
            <BrandLogo className="size-10 rounded-xl shadow-lg ring-1 ring-white/10" />
            <span>
              <span className="block text-sm font-semibold tracking-[0.2em]">AUTHENTIQ</span>
              <span className="block text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Public records
              </span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="border-border bg-card text-foreground hover:bg-card"
            >
              <Link to="/verify">Public verifier</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="border-border bg-card text-foreground hover:bg-card"
            >
              <Link to="/login">
                Sign in <ArrowRight />
              </Link>
            </Button>
          </div>
        </header>

        <main className="mt-10 flex-1 space-y-8">
          <section className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              Public registry
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
              Public records
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Every entry below was published by a creator who selected{" "}
              <span className="font-medium text-foreground">Public record</span> at registration. Search
              by creator name, title, or registration reference. Private and public-fingerprint records
              are never listed here, and the original file is never served.
            </p>
          </section>

          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile
              icon={<Fingerprint className="size-3.5" />}
              label="Public records"
              value={data ? String(data.total) : "—"}
              hint={hasFilters ? "matching your filters" : "published in the registry"}
            />
            <StatTile
              icon={<Users className="size-3.5" />}
              label="Creators"
              value={data ? String(data.total_creators) : "—"}
              hint="distinct public authors"
            />
            <StatTile
              icon={<Layers className="size-3.5" />}
              label="Asset types"
              value={data ? String(data.asset_types.length) : "—"}
              hint="categories on record"
            />
            <StatTile
              icon={<Sparkles className="size-3.5" />}
              label="Latest entry"
              value={data?.latest_registered_at ? formatDate(data.latest_registered_at, "MMM d, yyyy") : "—"}
              hint={data?.latest_registered_at ? relativeTime(data.latest_registered_at) : "nothing published yet"}
            />
          </section>

          <section className="rounded-xl border border-border bg-card/60 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={rawQuery}
                  onChange={(event) => setRawQuery(event.target.value)}
                  placeholder="Search creator names, titles, references or tags…"
                  aria-label="Search public records"
                  className="h-11 rounded-xl pl-9 pr-9"
                />
                {rawQuery ? (
                  <button
                    type="button"
                    onClick={() => setRawQuery("")}
                    aria-label="Clear search"
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <X className="size-3.5" />
                  </button>
                ) : null}
              </div>
              <select
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value);
                  setPage(1);
                }}
                aria-label="Sort records"
                className="h-11 rounded-xl border border-border bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="recent">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="title">Title A–Z</option>
                <option value="creator">Creator A–Z</option>
              </select>
            </div>

            {data?.asset_types.length ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setAssetType("");
                    setPage(1);
                  }}
                  className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${
                    assetType
                      ? "border-border text-muted-foreground hover:bg-accent"
                      : "border-foreground/25 bg-foreground/10 text-foreground"
                  }`}
                >
                  All types
                </button>
                {data.asset_types.map((entry) => (
                  <button
                    key={entry.value}
                    type="button"
                    onClick={() => {
                      setAssetType((current) => (current === entry.value ? "" : entry.value));
                      setPage(1);
                    }}
                    className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${
                      assetType === entry.value
                        ? "border-foreground/25 bg-foreground/10 text-foreground"
                        : "border-border text-muted-foreground hover:bg-accent"
                    }`}
                  >
                    {titleCase(entry.value)} · {entry.count}
                  </button>
                ))}
              </div>
            ) : null}
          </section>

          {recordsQuery.isError ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-6 text-sm text-destructive">
              The public registry could not be loaded. Please try again.
            </div>
          ) : null}

          {isInitialLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div
                  key={index}
                  className="h-64 animate-pulse rounded-xl border border-border bg-card/50"
                />
              ))}
            </div>
          ) : null}

          {!isInitialLoading && !recordsQuery.isError && items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/40 px-6 py-16 text-center">
              <Globe className="mx-auto size-8 text-muted-foreground" />
              <h2 className="mt-3 text-base font-semibold text-foreground">
                {hasFilters ? "No public records match that search" : "No public records published yet"}
              </h2>
              <p className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-muted-foreground">
                {hasFilters
                  ? "Try a different creator name, title or reference, or clear the filters."
                  : "Records appear here the moment a creator selects the Public record disclosure level while registering."}
              </p>
              {hasFilters ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4 border-border bg-transparent"
                  onClick={() => {
                    setRawQuery("");
                    setAssetType("");
                  }}
                >
                  Clear filters
                </Button>
              ) : null}
            </div>
          ) : null}

          {items.length ? (
            <div className={recordsQuery.isFetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {items.map((record) => (
                  <RecordCard key={record.registration_reference} record={record} />
                ))}
              </div>

              {pages > 1 ? (
                <div className="mt-6 flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-border bg-card text-foreground hover:bg-accent"
                    disabled={page <= 1}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                  >
                    <ChevronLeft /> Previous
                  </Button>
                  {pageNumbers.map((pageNumber) => (
                    <button
                      key={pageNumber}
                      type="button"
                      onClick={() => setPage(pageNumber)}
                      className={`size-8 rounded-lg border text-xs font-medium transition-colors ${
                        pageNumber === page
                          ? "border-foreground/25 bg-foreground/10 text-foreground"
                          : "border-border text-muted-foreground hover:bg-accent"
                      }`}
                    >
                      {pageNumber}
                    </button>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-border bg-card text-foreground hover:bg-accent"
                    disabled={page >= pages}
                    onClick={() => setPage((current) => Math.min(pages, current + 1))}
                  >
                    Next <ChevronRight />
                  </Button>
                </div>
              ) : null}

              <p className="mt-4 text-center text-[11px] text-muted-foreground">
                Showing {items.length} of {data?.total ?? 0} public record
                {(data?.total ?? 0) === 1 ? "" : "s"}
              </p>
            </div>
          ) : null}
        </main>

        <footer className="mt-12 border-t border-border/40 pt-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <ShieldCheck className="size-3.5" />
              {data?.privacy_note ??
                "Only records published as public are listed. Original files are never served."}
            </p>
            <div className="flex flex-wrap items-center gap-3 text-[11px]">
              <Link to="/verify" className="text-muted-foreground transition-colors hover:text-foreground">
                Public verifier
              </Link>
              <Link to="/login" className="text-muted-foreground transition-colors hover:text-foreground">
                Sign in
              </Link>
              <Link to="/register" className="text-muted-foreground transition-colors hover:text-foreground">
                Register a creation
              </Link>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
