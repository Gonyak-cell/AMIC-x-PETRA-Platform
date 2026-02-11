import { useState } from "react";
import { Card, Badge } from "@/components/ui";
import { HeroSection } from "@/components/gallery";
import { cn } from "@/lib/cn";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

interface NewsArticle {
  id: number;
  category: string;
  title: string;
  date: string;
  imageUrl: string;
}

const CATEGORIES = ["전체", "법인소식", "업무사례", "뉴스레터", "언론보도"] as const;

const BADGE_VARIANT: Record<string, "success" | "warning" | "info" | "neutral" | "error"> = {
  법인소식: "info",
  업무사례: "success",
  뉴스레터: "warning",
  언론보도: "neutral",
};

const MOCK_NEWS: NewsArticle[] = [
  {
    id: 1,
    category: "법인소식",
    title: "AMIC, 2026년 상반기 신규 파트너 합류 발표",
    date: "2026-02-10",
    imageUrl: "https://picsum.photos/seed/news1/600/450",
  },
  {
    id: 2,
    category: "업무사례",
    title: "국내 대형 M&A 거래 자문 — 2,000억원 규모 크로스보더 딜 성공",
    date: "2026-02-08",
    imageUrl: "https://picsum.photos/seed/news2/600/450",
  },
  {
    id: 3,
    category: "뉴스레터",
    title: "금융규제 동향 리포트 Vol.45 — ESG 공시 의무화 대응 전략",
    date: "2026-02-06",
    imageUrl: "https://picsum.photos/seed/news3/600/450",
  },
  {
    id: 4,
    category: "언론보도",
    title: "파이낸셜타임스 선정, 아시아 우수 법률자문사 Top 10",
    date: "2026-02-05",
    imageUrl: "https://picsum.photos/seed/news4/600/450",
  },
  {
    id: 5,
    category: "법인소식",
    title: "제3회 AMIC 포럼 — 디지털 전환과 법률 서비스의 미래",
    date: "2026-02-03",
    imageUrl: "https://picsum.photos/seed/news5/600/450",
  },
  {
    id: 6,
    category: "업무사례",
    title: "SPAC 합병 통한 상장 지원 — 바이오 스타트업 성공 사례",
    date: "2026-02-01",
    imageUrl: "https://picsum.photos/seed/news6/600/450",
  },
  {
    id: 7,
    category: "뉴스레터",
    title: "AI 규제 글로벌 비교 분석 — EU AI Act와 국내 법안 동향",
    date: "2026-01-30",
    imageUrl: "https://picsum.photos/seed/news7/600/450",
  },
  {
    id: 8,
    category: "언론보도",
    title: "한국경제 인터뷰 — 크로스보더 투자의 핵심 리스크와 대응 전략",
    date: "2026-01-28",
    imageUrl: "https://picsum.photos/seed/news8/600/450",
  },
  {
    id: 9,
    category: "법인소식",
    title: "Pro Bono 프로그램 확대 — 스타트업 법률 지원 MOU 체결",
    date: "2026-01-25",
    imageUrl: "https://picsum.photos/seed/news9/600/450",
  },
  {
    id: 10,
    category: "업무사례",
    title: "공정거래위원회 기업결합 심사 대응 — 글로벌 반도체 기업 자문",
    date: "2026-01-22",
    imageUrl: "https://picsum.photos/seed/news10/600/450",
  },
  {
    id: 11,
    category: "뉴스레터",
    title: "부동산 개발 금융 최신 규제 가이드 — 2026년 개정사항 정리",
    date: "2026-01-20",
    imageUrl: "https://picsum.photos/seed/news11/600/450",
  },
  {
    id: 12,
    category: "언론보도",
    title: "서울경제 기고 — 해외 펀드 구조화와 세무 쟁점",
    date: "2026-01-18",
    imageUrl: "https://picsum.photos/seed/news12/600/450",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NewsSamplePage() {
  const [activeTab, setActiveTab] = useState<string>("전체");

  const filtered =
    activeTab === "전체"
      ? MOCK_NEWS
      : MOCK_NEWS.filter((a) => a.category === activeTab);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <HeroSection
        title="소식자료"
        description="최신 법인소식, 업무사례, 뉴스레터 및 언론보도를 확인하세요."
        backgroundUrl="https://picsum.photos/seed/hero-news/1400/500"
        height="md"
      />

      {/* Category Tabs */}
      <div className="flex gap-1 border-b border-gray-border overflow-x-auto">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={cn(
              "shrink-0 px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === cat
                ? "text-amic border-b-2 border-accent"
                : "text-text-secondary hover:text-text-dark"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* News Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((article) => (
          <div key={article.id} className="cursor-pointer" role="button" tabIndex={0}>
            <Card variant="forest-lift" padding="none" className="overflow-hidden">
              <div className="aspect-[4/3] overflow-hidden bg-bg-cool">
                <img
                  src={article.imageUrl}
                  alt={article.title}
                  loading="lazy"
                  className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
                />
              </div>
              <div className="p-4 space-y-2">
                <Badge variant={BADGE_VARIANT[article.category] ?? "neutral"} pill>
                  {article.category}
                </Badge>
                <h3 className="font-heading font-semibold text-text-dark line-clamp-2 leading-snug">
                  {article.title}
                </h3>
                <p className="text-xs text-text-secondary">{article.date}</p>
              </div>
            </Card>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <p className="text-center text-xs text-text-muted">
        BKL 스타일 뉴스 컬렉션 레이아웃 프로토타입 — placeholder 이미지 사용
      </p>
    </div>
  );
}
