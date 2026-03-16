/** 홈 대시보드 — MY PROJECTS 캐러셀 섹션 */

import { useState, useEffect } from "react";
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

  // clamp activeIndex when list shrinks
  useEffect(() => {
    if (projects.length > 0 && activeIndex >= projects.length) {
      setActiveIndex(projects.length - 1);
    }
  }, [projects.length, activeIndex]);

  const active = projects[activeIndex];
  const len = projects.length;

  return (
    <div>
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

      {/* Active carousel */}
      {!isLoading && !isError && active && (
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Left: card + nav */}
          <div className="flex-1 min-w-0">
            <ProjectCarouselCard
              transaction={active}
              onClick={() => navigate(`/ma/transactions/${active.id}`)}
            />

            {/* Navigation */}
            {len > 1 && (
              <div className="flex items-center justify-between mt-3">
                <button
                  type="button"
                  aria-label="Previous project"
                  className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors bg-accent/10 text-accent hover:bg-accent/20"
                  onClick={() => setActiveIndex((i) => (i - 1 + len) % len)}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-text-secondary font-medium">
                  {activeIndex + 1} / {len}
                </span>
                <button
                  type="button"
                  aria-label="Next project"
                  className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors bg-accent/10 text-accent hover:bg-accent/20"
                  onClick={() => setActiveIndex((i) => (i + 1) % len)}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Right: summary panel */}
          <ProjectSummaryPanel transaction={active} userEmail={email!} />
        </div>
      )}
    </div>
  );
}
