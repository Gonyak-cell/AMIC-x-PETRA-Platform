import { useState, useMemo, useCallback, useRef } from "react";
import { Search } from "lucide-react";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { PageHero, SlidePanel } from "@/components/ui";
import type { LicenseType } from "@/modules/kiis/types/gpResearch";
import {
  useGPResearchList,
  useGPResearchDetail,
} from "@/modules/kiis/hooks/useGPResearch";
import { GPSegmentControl } from "@/modules/kiis/components/GPSegmentControl";
import { GPMasterList } from "@/modules/kiis/components/GPMasterList";
import { GPDetailOverlay } from "@/modules/kiis/components/GPDetailOverlay";
import heroImg from "@/assets/images/heroes/forestgp-vc.jpg";

export default function GPResearchPage() {
  const [selectedGPId, setSelectedGPId] = useState<string | null>(null);
  const [selectedLicenses, setSelectedLicenses] = useState<Set<LicenseType>>(
    new Set(["pef", "vc", "nta"]),
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const { data: gpData = [], isLoading } = useGPResearchList();
  const { data: selectedGP = null } = useGPResearchDetail(selectedGPId);

  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(value), 300);
  }, []);

  // 필터링 & 정렬
  const filteredData = useMemo(() => {
    let result = gpData;

    // 라이선스 필터
    if (selectedLicenses.size > 0) {
      result = result.filter((gp) =>
        gp.licenses.some((l) => selectedLicenses.has(l)),
      );
    }

    // 검색 필터
    if (debouncedQuery.trim()) {
      const q = debouncedQuery.trim().toLowerCase();
      result = result.filter(
        (gp) =>
          gp.name.toLowerCase().includes(q) ||
          gp.nameEn?.toLowerCase().includes(q) ||
          gp.keyPerson.toLowerCase().includes(q),
      );
    }

    // AUM 내림차순 정렬
    return [...result].sort((a, b) => b.cumAum - a.cumAum);
  }, [gpData, selectedLicenses, debouncedQuery]);

  const gridRef = useRef<HTMLDivElement>(null);
  useScrollReveal(gridRef, { stagger: 0.04, y: 16 }, [filteredData.length]);

  return (
    <div className="space-y-6">
      <PageHero
        title="GP Research"
        subtitle="운용사(GP) 전수 목록 · 라이선스별 필터 · 실적/포트폴리오/인력 심층 분석"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      {/* 세그먼트 컨트롤 + 검색 */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <GPSegmentControl
          selected={selectedLicenses}
          onChange={setSelectedLicenses}
        />
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="운용사명 검색..."
            className="w-full pl-10 pr-4 py-2 rounded-dr-sm border border-border bg-white text-sm text-text-dark placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 shadow-sm"
          />
        </div>
      </div>

      {/* 마스터 리스트 */}
      <div ref={gridRef}>
        {isLoading ? (
          <p className="py-12 text-center text-sm text-text-secondary">
            운용사 데이터를 불러오는 중...
          </p>
        ) : (
          <GPMasterList
            data={filteredData}
            selectedId={selectedGPId}
            onSelect={setSelectedGPId}
          />
        )}
      </div>

      {/* 상세 오버레이 */}
      <SlidePanel
        open={!!selectedGP}
        onClose={() => setSelectedGPId(null)}
        title={selectedGP?.name ?? ""}
        subtitle={selectedGP?.nameEn}
        width="xl"
      >
        {selectedGP && <GPDetailOverlay gp={selectedGP} />}
      </SlidePanel>
    </div>
  );
}
