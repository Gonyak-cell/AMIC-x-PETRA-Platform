import { FileSearch } from "lucide-react";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { useIBInsights } from "@/modules/kiis/hooks/useIBInsights";
import IBFactCard from "./IBFactCard";
import IBOpinionCard from "./IBOpinionCard";
import IBDisclaimerBanner from "./IBDisclaimerBanner";

interface IBInsightsPanelProps {
  corpCode: string;
}

export default function IBInsightsPanel({ corpCode }: IBInsightsPanelProps) {
  const { data, isLoading, isError } = useIBInsights(corpCode);

  if (isLoading) return <Spinner />;

  if (isError || !data) {
    return (
      <Card>
        <EmptyState
          icon={FileSearch}
          title="IB 인사이트 없음"
          description="이 운용사의 IB 매체 인사이트가 없습니다."
        />
      </Card>
    );
  }

  if (data.total_articles === 0) {
    return (
      <Card>
        <EmptyState
          icon={FileSearch}
          title="IB 인사이트 없음"
          description="수집된 IB 매체 기사가 없습니다."
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Fact 섹션 */}
      {data.facts.length > 0 && (
        <Card title="Fact" headerBar padding="none">
          <div className="divide-y divide-border">
            {data.facts.map((article) => (
              <IBFactCard key={article.id} article={article} />
            ))}
          </div>
        </Card>
      )}

      {/* Disclaimer */}
      {data.opinions.length > 0 && (
        <IBDisclaimerBanner text={data.disclaimer} />
      )}

      {/* Opinion 섹션 */}
      {data.opinions.length > 0 && (
        <Card title="Opinion" headerBar padding="none">
          <div className="divide-y divide-border">
            {data.opinions.map((article) => (
              <IBOpinionCard key={article.id} article={article} />
            ))}
          </div>
        </Card>
      )}

      {/* 마지막 수집 시간 */}
      {data.last_collected_at && (
        <p className="text-xs text-text-secondary text-right">
          Last collected:{" "}
          {new Date(data.last_collected_at).toLocaleString("ko-KR")}
        </p>
      )}
    </div>
  );
}
