import { useRef, useState } from "react";
import { PageHero } from "@/components/ui";
import { gsap, ScrollTrigger, useGSAP } from "@/lib/gsap";
import heroImg from "@/assets/images/forest-bg.jpg";
import { TeamMemberCard } from "./TeamMemberCard";
import { MemberDetailModal } from "./MemberDetailModal";

export interface TeamMemberData {
  name: string;
  title: string;
  org: string;
  career: { period: string; desc: string }[];
  education: { year: string; desc: string }[];
  qualifications?: string[];
}

const TEAM_MEMBERS: TeamMemberData[] = [
  {
    name: "김양태",
    title: "대표이사 · 공인회계사",
    org: "주식회사 페트라브릿지파트너스",
    career: [
      { period: "2026 ~ 현재", desc: "주식회사 페트라브릿지파트너스 대표이사" },
      {
        period: "2017 ~ 2025",
        desc: "KPMG 삼정회계법인 Deal Advisory 부문 파트너",
      },
      { period: "2016 ~ 2017", desc: "KPMG China 베이징 사무소 국제조세 부문" },
      { period: "2015 ~ 2016", desc: "KPMG 삼정회계법인 Deal Advisory 부문" },
      { period: "2013 ~ 2015", desc: "KCBC Beijing 세무자문" },
      { period: "2010 ~ 2013", desc: "딜로이트 안진회계법인 회계감사 부문" },
    ],
    education: [
      { year: "2015", desc: "중국 베이징 UIBE 경영석사(MBA) 졸업" },
      { year: "2013", desc: "서울시립대학교 세무학과 학사 졸업" },
    ],
    qualifications: ["공인회계사, 대한민국 (2010)"],
  },
  {
    name: "임영훈",
    title: "대표변호사",
    org: "법무법인 아믹",
    career: [
      { period: "2026 ~ 현재", desc: "법무법인 아믹 대표변호사" },
      { period: "2023 ~ 2025", desc: "법무법인 에스엘파트너스 대표변호사" },
      { period: "2021 ~ 2023", desc: "삼성전자 주식회사 법무팀 변호사" },
      { period: "2017 ~ 2021", desc: "김·장 법률사무소 변호사" },
      { period: "2011 ~ 2012", desc: "딜로이트 안진회계법인 공인회계사" },
    ],
    education: [
      { year: "2017", desc: "대법원 사법연수원 제46기 수료" },
      { year: "2015", desc: "연세대학교 경제학과 학사 졸업" },
    ],
    qualifications: ["변호사, 대한민국 (2017)", "공인회계사, 대한민국 (2010)"],
  },
  {
    name: "박병준",
    title: "대표변호사",
    org: "법무법인 아믹",
    career: [
      { period: "2026 ~ 현재", desc: "법무법인 아믹 대표변호사" },
      { period: "2024 ~ 2025", desc: "미국 고리컴퍼니 고문변호사" },
      { period: "2017 ~ 2024", desc: "김·장 법률사무소 변호사" },
      { period: "2015 ~ 2017", desc: "서울고등법원 재판연구원" },
      { period: "2012 ~ 2013", desc: "서울북부지방법원 법원사무관" },
    ],
    education: [
      { year: "2024", desc: "UC Berkeley School of Law, LL.M." },
      { year: "2021", desc: "서울대학교 대학원 법학과 석사 수료" },
      { year: "2015", desc: "대법원 사법연수원 제44기 수료" },
      { year: "2013", desc: "성균관대학교 물리학과 학사 졸업" },
    ],
    qualifications: [
      "변호사, 미국 (캘리포니아주, 2024 / 텍사스주, 2025)",
      "변호사, 대한민국 (2015)",
      "법원행정고등고시 (2011)",
    ],
  },
  {
    name: "조우상",
    title: "이사 · 컨설턴트",
    org: "주식회사 페트라브릿지파트너스",
    career: [
      { period: "2026 ~ 현재", desc: "주식회사 페트라브릿지파트너스 이사" },
      { period: "2017 ~ 2025", desc: "KPMG 삼정회계법인 Deal Advisory 부문" },
    ],
    education: [
      { year: "2015", desc: "프랑스 파리정치대학 공공정책경제학 석사 졸업" },
      { year: "2013", desc: "미국 브랜다이즈대학교 경제학 · 수학 학사 졸업" },
    ],
  },
  {
    name: "윤태리",
    title: "실장",
    org: "AMIC x PETRABRIDGE PARTNERS",
    career: [],
    education: [],
  },
  {
    name: "서지원",
    title: "대표변호사",
    org: "법무법인 아믹",
    career: [
      { period: "2026 ~ 현재", desc: "법무법인 아믹 대표변호사" },
      { period: "2024 ~ 2025", desc: "법무법인 에스엘파트너스 파트너변호사" },
      { period: "2020 ~ 2024", desc: "김·장 법률사무소 변호사" },
      { period: "2019 ~ 2020", desc: "국방부 법무관" },
      { period: "2018 ~ 2019", desc: "해군본부 법무관" },
      { period: "2017 ~ 2018", desc: "해병대 제1사단 법무관" },
    ],
    education: [
      { year: "2017", desc: "대법원 사법연수원 제46기 수료" },
      { year: "2015", desc: "서울대학교 교육학과 학사 졸업" },
    ],
    qualifications: ["변호사, 대한민국 (2017)"],
  },
];

export default function TeamPage() {
  const gridRef = useRef<HTMLDivElement>(null);
  const [selectedMember, setSelectedMember] = useState<TeamMemberData | null>(
    null,
  );

  useGSAP(
    () => {
      const el = gridRef.current;
      if (!el || !el.children.length) return;

      const cards = Array.from(el.children);

      gsap.set(cards, {
        opacity: 0,
        y: 60,
        scale: 0.9,
        rotateX: 8,
      });

      gsap.to(cards, {
        opacity: 1,
        y: 0,
        scale: 1,
        rotateX: 0,
        duration: 0.7,
        stagger: { each: 0.12, from: "start" },
        ease: "back.out(1.2)",
        scrollTrigger: {
          trigger: el,
          start: "top 80%",
          toggleActions: "play none none none",
        },
      });

      return () => {
        ScrollTrigger.getAll()
          .filter((t) => t.trigger === el)
          .forEach((t) => t.kill());
      };
    },
    { scope: gridRef },
  );

  return (
    <div className="space-y-6">
      <PageHero
        title="Our Team"
        subtitle="AMIC x PETRABRIDGE PARTNERS"
        backgroundImage={heroImg}
        backgroundOpacity={0.35}
        backgroundPosition="bottom"
        compact
      />

      <div>
        <h2 className="label-uppercase mb-4">Team Members</h2>
        <div
          ref={gridRef}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          style={{ perspective: "1000px" }}
        >
          {TEAM_MEMBERS.map((member) => (
            <TeamMemberCard
              key={member.name}
              member={member}
              onClick={() => setSelectedMember(member)}
            />
          ))}
        </div>
      </div>

      {selectedMember && (
        <MemberDetailModal
          member={selectedMember}
          onClose={() => setSelectedMember(null)}
        />
      )}
    </div>
  );
}
