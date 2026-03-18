/** 홈 대시보드 — MY PROJECTS 캐러셀 섹션 (Figma Cards 위젯 구조) */

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, FolderKanban, Inbox } from "lucide-react";
import { Card } from "@/components/ui";
import { useMyProjects } from "./useMyProjects";
import ProjectCarouselCard from "./ProjectCarouselCard";
import ProjectSummaryPanel from "./ProjectSummaryPanel";

export default function MyProjectsSection() {
  const navigate = useNavigate();
  const { projects, isLoading, isError, email } = useMyProjects();

  const [activeIndex, setActiveIndex] = useState(0);
  // phase: null(정지) → "exit"(퇴장) → "enter"(등장) → null
  const [phase, setPhase] = useState<"exit" | "enter" | null>(null);
  const [slideDir, setSlideDir] = useState<"left" | "right">("left");
  const [isAnimating, setIsAnimating] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (projects.length > 0 && activeIndex >= projects.length) {
      setActiveIndex(projects.length - 1);
    }
  }, [projects.length, activeIndex]);

  const active = projects[activeIndex];
  const len = projects.length;

  const slideTo = useCallback(
    (direction: "left" | "right") => {
      if (isAnimating || len <= 1) return;
      setIsAnimating(true);
      setSlideDir(direction);
      setPhase("exit");

      // Phase 1: 현재 카드 퇴장 (250ms)
      setTimeout(() => {
        // 인덱스 변경
        setActiveIndex((i) =>
          direction === "left" ? (i + 1) % len : (i - 1 + len) % len,
        );
        // Phase 2: 새 카드를 반대쪽에 즉시 배치 (트랜지션 없이)
        setPhase("enter");

        // Phase 3: 새 카드 슬라이드 인 (다음 프레임에서 트랜지션 시작)
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setPhase(null);
            setIsAnimating(false);
          });
        });
      }, 200);
    },
    [isAnimating, len],
  );

  return (
    <div className="h-full flex flex-col">
      <h2 className="label-uppercase mb-3">MY PROJECTS</h2>

      {/* Loading */}
      {isLoading && (
        <Card padding="md">
          <div className="flex gap-4 animate-pulse">
            <div className="w-12 h-12 rounded-lg bg-gray-100 shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-5 w-3/4 bg-gray-100 rounded" />
              <div className="h-4 w-1/2 bg-gray-100 rounded" />
              <div className="h-3 w-1/3 bg-gray-100 rounded" />
            </div>
          </div>
        </Card>
      )}

      {/* Error */}
      {!isLoading && isError && (
        <Card padding="md">
          <div className="flex flex-col items-center py-6 text-text-muted">
            <Inbox className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">프로젝트 정보를 불러올 수 없습니다</p>
          </div>
        </Card>
      )}

      {/* Empty */}
      {!isLoading && !isError && len === 0 && (
        <Card padding="md">
          <div className="flex flex-col items-center py-8 text-text-muted">
            <FolderKanban className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">현재 담당 중인 프로젝트가 없습니다</p>
          </div>
        </Card>
      )}

      {/* ── Active carousel — Figma "Cards" widget layout ── */}
      {!isLoading && !isError && active && (
        <div
          className="bg-white rounded-2xl overflow-hidden flex-1 flex flex-col"
          style={{
            boxShadow:
              "0px 16px 24px rgba(0,0,0,0.06), 0px 2px 6px rgba(0,0,0,0.04), 0px 0px 1px rgba(0,0,0,0.04)",
          }}
        >
          <div className="flex flex-col sm:flex-row">
            {/* Left: arrow + card + arrow */}
            <div className="flex-1 p-5 flex items-center gap-3">
              {/* Prev arrow */}
              {len > 1 && (
                <button
                  type="button"
                  aria-label="Previous project"
                  className="shrink-0 text-accent hover:text-accent/70 transition-colors disabled:opacity-30"
                  onClick={() => slideTo("right")}
                  disabled={isAnimating}
                >
                  <ChevronLeft className="w-5 h-5" strokeWidth={2.5} />
                </button>
              )}

              {/* Card — slide animation (exit → enter → idle) */}
              <div
                ref={cardRef}
                className="flex-1 min-w-0 overflow-hidden"
                style={{
                  transform:
                    phase === "exit"
                      ? // 퇴장: 진행 방향으로 밀려남
                        slideDir === "left"
                        ? "translateX(-110%)"
                        : "translateX(110%)"
                      : phase === "enter"
                        ? // 등장 대기: 반대쪽에 즉시 배치 (트랜지션 없이)
                          slideDir === "left"
                          ? "translateX(110%)"
                          : "translateX(-110%)"
                        : // 정지: 제자리
                          "translateX(0)",
                  opacity: phase === "enter" ? 0 : phase === "exit" ? 0 : 1,
                  transition:
                    phase === "enter"
                      ? "none"
                      : "transform 200ms ease-out, opacity 200ms ease-out",
                }}
              >
                <ProjectCarouselCard
                  transaction={active}
                  onClick={() => navigate(`/ma/transactions/${active.id}`)}
                />
              </div>

              {/* Next arrow */}
              {len > 1 && (
                <button
                  type="button"
                  aria-label="Next project"
                  className="shrink-0 text-accent hover:text-accent/70 transition-colors disabled:opacity-30"
                  onClick={() => slideTo("left")}
                  disabled={isAnimating}
                >
                  <ChevronRight className="w-5 h-5" strokeWidth={2.5} />
                </button>
              )}
            </div>

            {/* Vertical divider */}
            <div className="hidden sm:block w-px bg-gray-200 self-stretch" />

            {/* Right: summary panel */}
            <div className="sm:w-[320px] shrink-0">
              <ProjectSummaryPanel transaction={active} userEmail={email!} />
            </div>
          </div>

          {/* Bottom: counter bar */}
          {len > 1 && (
            <div className="border-t border-gray-100 px-5 py-3 flex items-center gap-4">
              {/* Progress bar */}
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-300"
                  style={{ width: `${((activeIndex + 1) / len) * 100}%` }}
                />
              </div>
              {/* Counter */}
              <span className="text-xs text-text-secondary font-medium whitespace-nowrap">
                {activeIndex + 1} / {len}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
