import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Newspaper, Download } from "lucide-react";
import { toast } from "sonner";
import { useNewsList, useCollectNews } from "@/modules/kiis/hooks/useNews";
import { useAuth } from "@/hooks/useAuth";
import { Card, Button, Input, Select, Badge, EmptyState, Spinner } from "@/components/ui";
import SentimentIndicator from "@/modules/kiis/components/SentimentIndicator";
import type { NewsSource } from "@/modules/kiis/types/news";
import { formatDate } from "@/lib/format";

const SOURCE_OPTIONS = [
  { value: "", label: "All Sources" },
  { value: "platum", label: "Platum" },
  { value: "dealsite", label: "Dealsite" },
];

export default function NewsListPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useNewsList({
    source: (source as NewsSource) || undefined,
    search: search || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    page,
    size: 20,
  });

  const collectNews = useCollectNews();

  const handleCollect = () => {
    collectNews.mutate(undefined, {
      onSuccess: () => toast.success("News collection started"),
      onError: () => toast.error("Failed to collect news"),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          News
        </h1>
        {user?.role === "ADMIN" && (
          <Button
            variant="accent"
            icon={Download}
            onClick={handleCollect}
            loading={collectNews.isPending}
          >
            Collect News
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 max-w-sm">
          <Input
            label="Search"
            placeholder="Search articles..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          label="Source"
          options={SOURCE_OPTIONS}
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
        />
        <Input
          label="From"
          type="date"
          value={startDate}
          onChange={(e) => {
            setStartDate(e.target.value);
            setPage(1);
          }}
        />
        <Input
          label="To"
          type="date"
          value={endDate}
          onChange={(e) => {
            setEndDate(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* News Cards */}
      {isLoading ? (
        <Spinner />
      ) : !data?.items?.length ? (
        <EmptyState
          icon={Newspaper}
          title="No news articles"
          description="Try adjusting your search or filters."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.items.map((article) => (
            <div
              key={article.id}
              className="cursor-pointer"
              onClick={() => navigate(`/kiis/news/${article.id}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/kiis/news/${article.id}`);
              }}
            >
              <Card
                padding="md"
                className="hover:shadow-md transition-shadow"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-medium text-text-dark line-clamp-2">
                      {article.title}
                    </h3>
                    <Badge variant="info" className="shrink-0">
                      {article.source}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-text-secondary">
                    <span>{formatDate(article.published_at, "short")}</span>
                    <SentimentIndicator
                      sentiment={article.sentiment}
                      score={article.sentiment_score}
                    />
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            className="px-3 py-1 text-sm rounded border border-gray-border disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="text-sm text-text-secondary">
            Page {page} of {Math.ceil(data.total / 20)}
          </span>
          <button
            className="px-3 py-1 text-sm rounded border border-gray-border disabled:opacity-40"
            disabled={page >= Math.ceil(data.total / 20)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
