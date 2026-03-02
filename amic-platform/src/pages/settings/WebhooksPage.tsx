import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Plus, Trash2, Play, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  useWebhooks,
  useCreateWebhook,
  useDeleteWebhook,
  useTestWebhook,
} from "@/hooks/useIntegrations";
import {
  Card,
  Button,
  Input,
  Badge,
  Modal,
  DataTable,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { WebhookConfig } from "@/types/integrations";
import { formatDate } from "@/lib/format";

const EVENT_OPTIONS = [
  "deal.created",
  "deal.updated",
  "deal.archived",
  "document.created",
  "document.completed",
  "document.failed",
  "alert.triggered",
];

export default function WebhooksPage() {
  const { hasPermission } = useAuth();
  const { data: webhooks = [], isLoading } = useWebhooks();
  const createWebhook = useCreateWebhook();
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();

  const [showCreate, setShowCreate] = useState(false);
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [secret, setSecret] = useState("");
  const [revealedSecrets, setRevealedSecrets] = useState<Set<string>>(
    new Set(),
  );

  if (!hasPermission("user:manage")) {
    return <Navigate to="/settings/profile" replace />;
  }

  const handleCreate = () => {
    createWebhook.mutate(
      { url, events: selectedEvents, secret: secret || undefined },
      {
        onSuccess: () => {
          setShowCreate(false);
          setUrl("");
          setSelectedEvents([]);
          setSecret("");
        },
      },
    );
  };

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event],
    );
  };

  const toggleSecretReveal = (id: string) => {
    setRevealedSecrets((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const columns: Column<WebhookConfig>[] = [
    {
      key: "url",
      header: "URL",
      render: (row) => (
        <span className="text-sm font-mono truncate max-w-[250px] block">
          {row.url}
        </span>
      ),
    },
    {
      key: "events",
      header: "Events",
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.events.slice(0, 2).map((e) => (
            <Badge key={e} variant="neutral" className="text-xs">
              {e}
            </Badge>
          ))}
          {row.events.length > 2 && (
            <Badge variant="neutral" className="text-xs">
              +{row.events.length - 2}
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: "is_active",
      header: "Status",
      render: (row) => (
        <Badge variant={row.is_active ? "success" : "neutral"}>
          {row.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      key: "secret",
      header: "Secret",
      render: (row) => (
        <div className="flex items-center gap-1">
          <span className="text-xs font-mono">
            {row.secret
              ? revealedSecrets.has(row.id)
                ? row.secret
                : "••••••••"
              : "—"}
          </span>
          {row.secret && (
            <button
              className="text-text-secondary hover:text-text-dark"
              onClick={() => toggleSecretReveal(row.id)}
              aria-label="Toggle secret visibility"
            >
              {revealedSecrets.has(row.id) ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>
      ),
    },
    {
      key: "last_triggered_at",
      header: "Last Triggered",
      render: (row) =>
        row.last_triggered_at
          ? formatDate(row.last_triggered_at, "short")
          : "Never",
    },
    {
      key: "_actions",
      header: "Actions",
      width: "120px",
      render: (row) => (
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            icon={Play}
            onClick={() => testWebhook.mutate(row.id)}
            loading={testWebhook.isPending}
            aria-label="Test webhook"
          />
          <Button
            variant="ghost"
            size="sm"
            icon={Trash2}
            onClick={() => deleteWebhook.mutate(row.id)}
            aria-label="Delete webhook"
          />
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-dark">
            Webhooks
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Configure webhook endpoints for event notifications
          </p>
        </div>
        <Button
          variant="accent"
          size="sm"
          icon={Plus}
          onClick={() => setShowCreate(true)}
        >
          Create Webhook
        </Button>
      </div>

      {webhooks.length === 0 && !isLoading ? (
        <EmptyState
          title="No webhooks configured"
          description="Create a webhook to receive event notifications via HTTP POST."
        />
      ) : (
        <Card>
          <DataTable
            data={webhooks}
            columns={columns}
            keyField="id"
            emptyMessage="No webhooks"
          />
        </Card>
      )}

      {/* Create Modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Webhook"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              onClick={handleCreate}
              loading={createWebhook.isPending}
              disabled={!url || selectedEvents.length === 0}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Webhook URL"
            placeholder="https://example.com/webhook"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <div>
            <label className="label-uppercase mb-2 block">Events</label>
            <div className="flex flex-wrap gap-2">
              {EVENT_OPTIONS.map((event) => (
                <button
                  key={event}
                  onClick={() => toggleEvent(event)}
                  className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                    selectedEvents.includes(event)
                      ? "bg-amic text-white border-amic"
                      : "bg-white text-text-secondary border-gray-border hover:border-amic"
                  }`}
                >
                  {event}
                </button>
              ))}
            </div>
          </div>
          <Input
            label="Secret (optional)"
            placeholder="Signing secret for HMAC verification"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
}
