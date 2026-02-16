import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Newspaper, Download } from "lucide-react";
import { toast } from "sonner";
import { useNewsList, useCollectNews } from "@/modules/kiis/hooks/useNews";
import { useAuth } from "@/hooks/useAuth";
import { Card, Button, Input, Select, Badge, EmptyState, Spinner, Pagination, PageHero } from "@/components/ui";
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
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useNewsList({
    source: (source as NewsSource) || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    page,
    size: 20,
  });

  const collectNews = useCollectNews();

  const handleCollect = () => {
    collectNews.mutate(undefined, {
      onSuccess: (res) => {
        const total = Array.isArray(res)
          ? res.reduce((sum, r) => sum + r.collected, 0)
          : 0;
        toast.success(
          total > 0
            ? `${total} articles collected`
            : "News collection started",
        );
      },
      onError: (err: Error) =>
        toast.error(`News collection failed: ${err.message}`),
    });
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="News"
        subtitle="PE & VC industry news and analysis"
        compact
        actions={
          user?.role === "ADMIN" ? (
            <Button
              variant="accent"
              icon={Download}
              onClick={handleCollect}
              loading={collectNews.isPending}
            >
              Collect News
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
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
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(1);
          }}
        />
        <Input
          label="To"
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
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
          description="Try adjusting your filters."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.items.map((article) => (
            <button
              key={article.id}
              type="button"
              aria-label={`View article: ${article.title.slice(0, 60)}${article.title.length > 60 ? "…" : ""}`}
              className="cursor-pointer w-full text-left"
              onClick={() => navigate(`/kiis/news/${article.id}`)}
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
                    <SentimentIndicator score={article.sentiment_score} />
                  </div>
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}

      <Pagination
        page={page}
        totalPages={data ? Math.ceil(data.total / 20) : 0}
        onPageChange={setPage}
      />
    </div>
  );
}
