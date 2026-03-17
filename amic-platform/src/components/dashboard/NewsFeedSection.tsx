/** 대시보드 M&A 뉴스 피드 섹션 — 네이버 뉴스스탠드 스타일 */

import { useState, useMemo } from "react";
import {
  Newspaper,
  ExternalLink,
  Lock,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { Card } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useNewsFeed, type NewsFeedItem } from "./useNewsFeed";

/* ── 카테고리 / 소스 필터 상수 ─────────────────── */

const CATEGORIES = [
  { value: "", label: "전체" },
  { value: "ma", label: "M&A" },
  { value: "governance", label: "거버넌스" },
  { value: "fund", label: "펀드" },
] as const;

const SOURCES = [
  { value: "", label: "전체", group: "all" },
  { value: "dealsite", label: "딜사이트", group: "kiis" },
  { value: "investchosun", label: "인베스트조선", group: "kiis" },
  { value: "ibtomato", label: "IB토마토", group: "kiis" },
  { value: "bizwatch", label: "비즈워치", group: "kiis" },
] as const;

const PAGE_SIZE = 8;

/* ── 상대 시간 포맷터 ──────────────────────────── */

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "방금";
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}일 전`;
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    month: "short",
    day: "numeric",
  });
}

/* ── 개별 뉴스 아이템 ──────────────────────────── */

function NewsItem({ item }: { item: NewsFeedItem }) {
  return (
    <a
      href={item.canonical_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start gap-3 px-4 py-3 hover:bg-surface-hover transition-colors border-b border-border last:border-b-0"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <h4 className="text-sm font-medium text-text-dark truncate group-hover:text-accent transition-colors">
            {item.is_paywalled && (
              <Lock className="inline-block w-3.5 h-3.5 mr-1 text-text-muted" />
            )}
            {item.title}
          </h4>
          <ExternalLink className="w-3 h-3 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
        </div>
        {item.lead_text && (
          <p className="text-xs text-text-secondary line-clamp-1 mb-1">
            {item.lead_text}
          </p>
        )}
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span className="font-medium text-accent/80">
            {item.source_display}
          </span>
          {item.category_display !== "미분류" && (
            <>
              <span className="text-border">·</span>
              <span>{item.category_display}</span>
            </>
          )}
        </div>
      </div>
      <span className="text-xs text-text-muted whitespace-nowrap mt-0.5">
        {timeAgo(item.published_at)}
      </span>
    </a>
  );
}

/* ── 메인 컴포넌트 ─────────────────────────────── */

export default function NewsFeedSection() {
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSource, setSelectedSource] = useState("");
  const [page, setPage] = useState(1);

  const { items, total, isLoading, isError, apiError, refetch } = useNewsFeed({
    source: selectedSource || undefined,
    category: selectedCategory || undefined,
    page,
    size: PAGE_SIZE,
  });

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / PAGE_SIZE)),
    [total],
  );

  // 필터 변경 시 페이지 리셋
  const handleCategoryChange = (value: string) => {
    setSelectedCategory(value);
    setPage(1);
  };
  const handleSourceChange = (value: string) => {
    setSelectedSource(value);
    setPage(1);
  };

  return (
    <div>
      <h2 className="label-uppercase mb-3">M&A Industry News</h2>
      <Card padding="none">
        {/* 에러 배너 */}
        {apiError && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 text-xs border-b border-amber-200">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        <div className="flex min-h-[360px]">
          {/* ── 좌측: 필터 패널 ── */}
          <aside className="w-36 lg:w-40 border-r border-border flex-shrink-0 py-3">
            {/* 카테고리 필터 */}
            <div className="px-3 mb-3">
              <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1.5">
                카테고리
              </p>
              <ul className="space-y-0.5">
                {CATEGORIES.map((cat) => (
                  <li key={cat.value}>
                    <button
                      onClick={() => handleCategoryChange(cat.value)}
                      className={cn(
                        "w-full text-left text-xs px-2 py-1 rounded transition-colors",
                        selectedCategory === cat.value
                          ? "bg-accent/10 text-accent font-semibold"
                          : "text-text-secondary hover:text-text-dark hover:bg-surface-hover",
                      )}
                    >
                      {selectedCategory === cat.value && (
                        <span className="mr-1">●</span>
                      )}
                      {cat.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* 구분선 */}
            <div className="mx-3 border-t border-border mb-3" />

            {/* 소스 필터 */}
            <div className="px-3">
              <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1.5">
                소스별
              </p>
              <ul className="space-y-0.5">
                {SOURCES.map((src) => (
                  <li key={src.value}>
                    <button
                      onClick={() => handleSourceChange(src.value)}
                      className={cn(
                        "w-full text-left text-xs px-2 py-1 rounded transition-colors",
                        selectedSource === src.value
                          ? "bg-accent/10 text-accent font-semibold"
                          : "text-text-secondary hover:text-text-dark hover:bg-surface-hover",
                      )}
                    >
                      {selectedSource === src.value && (
                        <span className="mr-1">●</span>
                      )}
                      {src.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>

          {/* ── 우측: 뉴스 리스트 ── */}
          <div className="flex-1 flex flex-col">
            {isLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-2 text-text-muted">
                  <Newspaper className="w-8 h-8 animate-pulse" />
                  <span className="text-xs">뉴스를 불러오는 중...</span>
                </div>
              </div>
            ) : isError ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-2 text-red-400">
                  <AlertCircle className="w-8 h-8" />
                  <span className="text-xs text-text-secondary">
                    뉴스를 불러오지 못했습니다
                  </span>
                  <button
                    onClick={() => refetch()}
                    className="text-xs text-accent hover:underline mt-1"
                  >
                    다시 시도
                  </button>
                </div>
              </div>
            ) : items.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-2 text-text-muted">
                  <Newspaper className="w-8 h-8" />
                  <span className="text-xs">표시할 뉴스가 없습니다</span>
                </div>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto">
                  {items.map((item) => (
                    <NewsItem key={item.id} item={item} />
                  ))}
                </div>

                {/* 페이지네이션 */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-surface-subtle">
                    <span className="text-xs text-text-muted">
                      총 {total}건
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page <= 1}
                        className="p-1 rounded hover:bg-surface-hover disabled:opacity-30 transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-xs text-text-secondary min-w-[60px] text-center">
                        {page} / {totalPages}
                      </span>
                      <button
                        onClick={() =>
                          setPage((p) => Math.min(totalPages, p + 1))
                        }
                        disabled={page >= totalPages}
                        className="p-1 rounded hover:bg-surface-hover disabled:opacity-30 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
