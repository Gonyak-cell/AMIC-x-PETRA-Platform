import { useParams, Link } from "react-router-dom";
import { Newspaper, ExternalLink } from "lucide-react";
import { useNewsDetail } from "@/modules/kiis/hooks/useNews";
import { Card, Badge, Spinner, EmptyState } from "@/components/ui";
import SentimentIndicator from "@/modules/kiis/components/SentimentIndicator";
import { formatDate } from "@/lib/format";

export default function NewsDetailPage() {
  const { articleId } = useParams<{ articleId: string }>();
  const { data: article, isLoading } = useNewsDetail(articleId!);

  if (isLoading) return <Spinner />;
  if (!article) {
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
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          {article.title}
        </h1>
        <div className="mt-2 flex items-center gap-3 text-sm text-text-secondary">
          <Badge variant="info">{article.source}</Badge>
          <span>{formatDate(article.published_at, "long")}</span>
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline inline-flex items-center gap-1"
            >
              Original <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      {/* Sentiment */}
      <Card title="Sentiment Analysis" headerBar>
        <SentimentIndicator
          sentiment={article.sentiment}
          score={article.sentiment_score}
          className="text-sm"
        />
      </Card>

      {/* Content */}
      <Card title="Article" headerBar>
        <div className="prose prose-sm max-w-none text-text-body whitespace-pre-wrap">
          {article.content ?? "Content not available."}
        </div>
      </Card>

      {/* Related Companies */}
      {article.company_associations?.length > 0 && (
        <Card title="Related Companies" headerBar>
          <div className="flex flex-wrap gap-2">
            {article.company_associations.map((company) => (
              <Link
                key={company}
                to={`/kiis/companies/${company}`}
                className="px-3 py-1 text-sm bg-bg-cool rounded-full text-text-dark hover:bg-gray-200 transition-colors"
              >
                {company}
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
