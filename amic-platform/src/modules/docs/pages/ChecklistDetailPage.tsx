import { useNavigate } from "react-router-dom";
import { ArrowRight, ListChecks, CalendarClock } from "lucide-react";
import { Card, EmptyState, PageHero } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-dome.jpg";

interface Props {
  type: "closing" | "timeline";
}

const META = {
  closing: {
    title: "Closing Checklist",
    subtitle: "M&A 거래의 클로징 체크리스트를 관리합니다",
    icon: ListChecks,
    emptyTitle: "거래 워크스페이스에서 관리",
    emptyDesc:
      "클로징 체크리스트는 M&A 거래 워크스페이스에서 관리됩니다. 거래를 선택하여 체크리스트를 확인하세요.",
    actionLabel: "거래 목록 보기",
  },
  timeline: {
    title: "Deal Timeline",
    subtitle: "M&A 거래의 타임라인과 일정을 관리합니다",
    icon: CalendarClock,
    emptyTitle: "거래 워크스페이스에서 관리",
    emptyDesc:
      "딜 타임라인은 M&A 거래 워크스페이스에서 관리됩니다. 거래를 선택하여 타임라인을 확인하세요.",
    actionLabel: "거래 목록 보기",
  },
} as const;

export default function ChecklistDetailPage({ type }: Props) {
  const navigate = useNavigate();
  const m = META[type];

  return (
    <div className="space-y-6">
      <PageHero
        title={m.title}
        subtitle={m.subtitle}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />
      <Card padding="lg">
        <EmptyState
          icon={ArrowRight}
          title={m.emptyTitle}
          description={m.emptyDesc}
          actionLabel={m.actionLabel}
          onAction={() => navigate("/ma/transactions")}
        />
      </Card>
    </div>
  );
}
