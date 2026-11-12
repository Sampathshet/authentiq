import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, CheckCheck, Inbox, ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { Pagination } from "@/components/common/pagination";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, extractErrorMessage } from "@/lib/api";
import type { NotificationItem } from "@/lib/types";
import { relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface NotificationResponse {
  items: NotificationItem[];
  total: number;
  unread: number;
  page: number;
  page_size: number;
  pages: number;
}

const categories = ["security", "transfer", "dispute", "ownership", "team", "contribution", "verification", "account", "provenance"];

function targetFor(item: NotificationItem): string | null {
  switch (item.entity_type) {
    case "registration":
      return item.entity_id ? `/registrations/${item.entity_id}` : "/timeline";
    case "team_project":
      return item.entity_id ? `/teams/${item.entity_id}` : "/teams";
    case "dispute":
      return item.entity_id ? `/disputes/${item.entity_id}` : "/disputes";
    case "transfer":
      return "/transfers";
    case "verification_request":
      return "/anonymous-verification";
    case "session":
    case "user":
      return "/settings";
    default:
      return null;
  }
}

export default function NotificationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState("all");
  const [category, setCategory] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const notificationsQuery = useQuery({
    queryKey: ["notifications", page, tab, category],
    queryFn: () =>
      api.get<NotificationResponse>(`/notifications?page=${page}&page_size=20${tab === "unread" ? "&unread_only=true" : ""}${category ? `&category=${category}` : ""}`),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  };

  const openNotification = async (item: NotificationItem) => {
    if (!item.is_read) {
      try {
        await api.patch(`/notifications/${item.id}/read`);
        refresh();
      } catch (caught) {
        toast.error(extractErrorMessage(caught));
      }
    }
    const target = targetFor(item);
    if (target) navigate(target);
  };

  const markAll = async () => {
    try {
      const response = await api.post<{ message: string }>("/notifications/read-all");
      toast.success(response.message);
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const remove = async (item: NotificationItem) => {
    setBusyId(item.id);
    try {
      await api.delete(`/notifications/${item.id}`);
      toast.success("Notification dismissed");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusyId(null);
    }
  };

  const data = notificationsQuery.data;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Notification center"
        title="Workspace activity"
        description="Security events, transfer requests, team invitations, ownership approvals, verification outcomes, and dispute updates."
        actions={
          <Button variant="outline" size="sm" onClick={markAll} disabled={!data?.unread}>
            <CheckCheck /> Mark all read
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Total notifications</p>
          <p className="mt-2 text-2xl font-semibold">{data?.total ?? 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Unread</p>
          <p className="mt-2 text-2xl font-semibold">{data?.unread ?? 0}</p>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Tabs value={tab} onValueChange={(value) => { setTab(value); setPage(1); }}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="unread">Unread</TabsTrigger>
          </TabsList>
        </Tabs>
        <Select value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }} className="ml-auto w-[190px]" aria-label="Filter by category">
          <option value="">All categories</option>
          {categories.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
        </Select>
      </div>

      {notificationsQuery.isLoading && <LoadingBlock rows={6} />}
      {notificationsQuery.isError && <ErrorState error={notificationsQuery.error} onRetry={() => notificationsQuery.refetch()} />}

      {!notificationsQuery.isLoading && !notificationsQuery.isError && !data?.items.length && (
        <EmptyState
          icon={<Inbox className="size-5" />}
          title={tab === "unread" ? "No unread notifications" : "No notifications in this view"}
          description="Notifications are generated by real workspace events such as sign-ins from new devices, team invitations, transfer decisions, and dispute status changes."
        />
      )}

      {!!data?.items.length && (
        <div className="space-y-2">
          {data.items.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex gap-3 rounded-xl border p-4 transition-colors",
                item.is_read ? "border-border/60 bg-card/40" : "border-foreground/20 bg-blue-500/5",
              )}
            >
              <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", item.type === "security" ? "bg-secondary text-foreground" : "bg-accent/15 text-foreground")}>
                {item.type === "security" ? <ShieldCheck className="size-4" /> : <Bell className="size-4" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">{item.title}</p>
                  <Badge variant={item.is_read ? "slate" : "blue"}>{item.is_read ? "Read" : "Unread"}</Badge>
                  <Badge variant="outline">{titleCase(item.type)}</Badge>
                  <span className="text-[10px] text-muted-foreground">{relativeTime(item.created_at)}</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{item.message}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {!item.is_read && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        setBusyId(item.id);
                        try {
                          await api.patch(`/notifications/${item.id}/read`);
                          refresh();
                        } catch (caught) {
                          toast.error(extractErrorMessage(caught));
                        } finally {
                          setBusyId(null);
                        }
                      }}
                      loading={busyId === item.id}
                    >
                      <Check /> Mark read
                    </Button>
                  )}
                  {targetFor(item) && (
                    <Button size="sm" variant="ghost" onClick={() => openNotification(item)}>Open related record</Button>
                  )}
                  <Button size="sm" variant="ghost" className="text-destructive" onClick={() => remove(item)} loading={busyId === item.id}>
                    <Trash2 /> Dismiss
                  </Button>
                </div>
              </div>
            </div>
          ))}
          <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} disabled={notificationsQuery.isFetching} />
        </div>
      )}
    </div>
  );
}
