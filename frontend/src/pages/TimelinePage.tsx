import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Fingerprint, Filter, Layers, PlusCircle, ShieldCheck } from "lucide-react";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { SearchInput } from "@/components/common/search-input";
import { Pagination } from "@/components/common/pagination";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { HashValue } from "@/components/common/hash-value";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Paginated, Registration } from "@/lib/types";
import { assetTypeOptions, formatBytes, formatDate, relativeTime, titleCase } from "@/lib/format";

export default function TimelinePage() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [assetType, setAssetType] = useState("");
  const [sort, setSort] = useState("recent");

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["registrations", page, query, assetType, sort],
    queryFn: () =>
      api.get<Paginated<Registration>>(
        `/registrations?page=${page}&page_size=12&sort=${sort}${query ? `&q=${encodeURIComponent(query)}` : ""}${assetType ? `&asset_type=${assetType}` : ""}`,
      ),
  });

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Creative timeline"
        title="Your ownership record"
        description="A chronological view of every fingerprinted creation, its commitments, and its ledger state."
        actions={
          <Button asChild variant="gradient" size="sm">
            <Link to="/register">
              <PlusCircle /> Register creation
            </Link>
          </Button>
        }
      />

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center">
          <SearchInput value={query} onChange={(value) => { setQuery(value); setPage(1); }} placeholder="Search title, reference, fingerprint, or file name" className="flex-1" />
          <div className="flex gap-2">
            <Select
              value={assetType}
              onChange={(event) => { setAssetType(event.target.value); setPage(1); }}
              className="w-[170px]"
              aria-label="Filter by asset type"
            >
              <option value="">All asset types</option>
              {assetTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </Select>
            <Select value={sort} onChange={(event) => { setSort(event.target.value); setPage(1); }} className="w-[150px]" aria-label="Sort order">
              <option value="recent">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="title">Title A-Z</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {isLoading && <LoadingBlock rows={6} />}
      {isError && <ErrorState error={error} onRetry={() => refetch()} />}
      {!isLoading && !isError && !data?.items.length && (
        <EmptyState
          icon={<Fingerprint className="size-5" />}
          title="No creations match this view"
          description={query || assetType ? "Adjust the filters, or register a new creation to begin the record." : "Your timeline is empty. Register your first original file to create a real fingerprint and ledger entry."}
          action={
            <Button asChild>
              <Link to="/register">Register a creation</Link>
            </Button>
          }
        />
      )}

      <div className="space-y-2">
        {data?.items.map((registration) => (
          <Link
            key={registration.id}
            to={`/registrations/${registration.id}`}
            className="group block rounded-xl border border-border/70 bg-card/60 p-4 transition-all hover:border-accent/50 hover:bg-accent/30 hover:shadow-soft"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-foreground">
                <Fingerprint className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-semibold">{registration.title}</h3>
                  {registration.pending_ownership && <Badge variant="amber">Incoming ownership</Badge>}
                  <StatusBadge status={registration.pending_ownership ? "pending_recipient" : registration.status} />
                  <LedgerBadge mode={registration.ledger_mode} />
                  {registration.version > 1 && <Badge variant="outline">v{registration.version}</Badge>}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {registration.registration_id} · {titleCase(registration.asset_type)} · {formatBytes(registration.file_size)} · registered {relativeTime(registration.registered_at)}
                  {registration.pending_ownership ? " · ownership pending confirmation" : ""}
                </p>
                {registration.description && <p className="mt-2 line-clamp-2 max-w-3xl text-xs leading-relaxed text-muted-foreground">{registration.description}</p>}
                <div className="mt-2.5 flex flex-wrap items-center gap-x-5 gap-y-1.5">
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span className="font-medium text-foreground/80">SHA-256</span>
                    <HashValue value={registration.sha256} label="SHA-256" head={10} tail={8} />
                  </span>
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <Layers className="size-3" />
                    {registration.version} version{registration.version === 1 ? "" : "s"}
                  </span>
                  <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <ShieldCheck className="size-3" />
                    {titleCase(registration.privacy)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{formatDate(registration.registered_at)}</span>
                </div>
              </div>
              <ArrowUpRight className="hidden size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground sm:block" />
            </div>
          </Link>
        ))}
      </div>

      {!!data?.items.length && (
        <Pagination page={data.page} pages={data.pages} total={data.total} onPageChange={setPage} disabled={isFetching} />
      )}

      <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/40 px-4 py-3 text-[11px] text-muted-foreground">
        <Filter className="size-3.5" />
        Filters are executed by the authenticated API against your permitted records. Records are never fabricated client-side.
      </div>
    </div>
  );
}
