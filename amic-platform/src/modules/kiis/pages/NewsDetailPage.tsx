import { useParams, Link } from "react-router-dom";
import { Newspaper } from "lucide-react";
import { useNewsDetail } from "@/modules/kiis/hooks/useNews";
import { Card, Spinner, EmptyState, PageHero } from "@/components/ui";
import SentimentIndicator from "@/modules/kiis/components/SentimentIndicator";
import { formatDate } from "@/lib/format";
import heroImg from "@/assets/images/heroes/forestgp-forest.jpg";

export default function NewsDetailPage() {
  const { articleId } = useParams<{ articleId: string }>();
  const numId = Number(articleId);
  const { data: article, isLoading, isError } = useNewsDetail(numId);

  if (isNaN(numId)) {
    return (
      <EmptyState
        icon={Newspaper}
        title="Invalid article ID"
        description="The article ID in the URL is not valid."
      />
    );
  }

  if (isLoading) return <Spinner />;
  if (isError || !article) {
    return (
      <EmptyState
        icon={Newspaper}
        title="Article not found"
        description="The requested article could not be found."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/news" className="hover:text-accent">
          News
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark line-clamp-1">{article.title}</span>
      </div>

      {/* Header */}
      <PageHero
        title={article.title}
        subtitle={[
          article.source,
          article.author && `by ${article.author}`,
          formatDate(article.published_at, "long"),
        ].filter(Boolean).join(" | ")}
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      {/* Sentiment */}
      <Card title="Sentiment Analysis" headerBar>
        <SentimentIndicator
          score={article.sentiment_score}
          className="text-sm"
        />
      </Card>

      {/* Summary */}
      {article.summary && (
        <Card title="Summary" headerBar>
          <p className="text-text-body text-sm">{article.summary}</p>
        </Card>
      )}

      {/* Content */}
      <Card title="Article" headerBar>
        <div className="prose prose-sm max-w-none text-text-body whitespace-pre-wrap">
          {article.content ?? "Content not available."}
        </div>
      </Card>

      {/* Keywords */}
      {article.keywords && (
        <Card title="Keywords" headerBar>
          <div className="flex flex-wrap gap-2">
            {article.keywords
              .split(",")
              .map((kw) => kw.trim())
              .filter(Boolean)
              .map((kw) => (
                <span
                  key={kw}
                  className="px-3 py-1 text-sm bg-bg-cool rounded-full text-text-dark"
                >
                  {kw}
                </span>
              ))}
          </div>
        </Card>
      )}
    </div>
  );
}
