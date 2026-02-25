import type { LucideIcon } from "lucide-react";
import {
  FileText,
  Scale,
  SearchCheck,
  ClipboardCheck,
  BookOpen,
  MessageSquareText,
  ShieldCheck,
  Handshake,
  BarChart2,
  Gavel,
  Monitor,
  ListChecks,
  CalendarClock,
  FileSignature,
} from "lucide-react";

export type SubTypeStatus = "available" | "coming_soon" | "requires_context";

export interface SubType {
  id: string;
  label: string;
  labelKo: string;
  description: string;
  status: SubTypeStatus;
  createPath?: string;
  icon: LucideIcon;
  colorCls: string;
  bgCls: string;
}

export interface DocumentCategory {
  id: string;
  label: string;
  labelKo: string;
  description: string;
  icon: LucideIcon;
  colorCls: string;
  bgCls: string;
  subTypes: SubType[];
}

export const STUDIO_CATEGORIES: DocumentCategory[] = [
  {
    id: "marketing",
    label: "Marketing",
    labelKo: "마케팅 자료",
    description: "TM, IM, DM 등 투자자 대상 마케팅 문서를 생성합니다",
    icon: FileText,
    colorCls: "text-text-secondary",
    bgCls: "bg-gray-100",
    subTypes: [
      {
        id: "tm",
        label: "Teaser Memorandum",
        labelKo: "티저 메모",
        description: "잠재 투자자 대상 간결한 투자 개요",
        status: "available",
        createPath: "/docs/new?type=teaser",
        icon: FileText,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "im",
        label: "Information Memorandum",
        labelKo: "투자설명서",
        description: "상세 기업·재무·시장 분석 포함 종합 문서",
        status: "available",
        createPath: "/docs/new?type=im",
        icon: BookOpen,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "dm",
        label: "Discussion Memorandum",
        labelKo: "논의자료",
        description: "초기 논의 및 협의용 자료",
        status: "coming_soon",
        icon: MessageSquareText,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
    ],
  },
  {
    id: "legal",
    label: "Legal",
    labelKo: "법률 문서",
    description: "NDA, MOU, SPA 등 M&A 법률 문서를 생성합니다",
    icon: Scale,
    colorCls: "text-text-secondary",
    bgCls: "bg-gray-100",
    subTypes: [
      {
        id: "nda",
        label: "NDA",
        labelKo: "비밀유지계약",
        description: "거래 초기 비밀유지계약 (Bilateral / Unilateral)",
        status: "coming_soon",
        icon: ShieldCheck,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "mou",
        label: "MOU",
        labelKo: "양해각서",
        description: "Memorandum of Understanding",
        status: "available",
        createPath: "/docs/legal/new?type=MOU",
        icon: Handshake,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "deal_contracts",
        label: "Deal Contracts",
        labelKo: "거래 계약서",
        description: "SPA, SHA, BTA, SSA — 주요 거래 계약서",
        status: "available",
        createPath: "/docs/legal/new",
        icon: FileSignature,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
    ],
  },
  {
    id: "due_diligence",
    label: "Due Diligence",
    labelKo: "실사 보고서",
    description: "FDD, LDD, TDD 등 실사 보고서를 생성합니다",
    icon: SearchCheck,
    colorCls: "text-text-secondary",
    bgCls: "bg-gray-100",
    subTypes: [
      {
        id: "fdd",
        label: "FDD",
        labelKo: "재무실사",
        description: "Financial Due Diligence — QoE, NWC, Net Debt",
        status: "available",
        createPath: "/docs/new?type=fdd",
        icon: BarChart2,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "ldd",
        label: "LDD",
        labelKo: "법률실사",
        description: "Legal Due Diligence — 10개 섹션 체크리스트",
        status: "available",
        createPath: "/docs/ldd/new",
        icon: Gavel,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "tdd",
        label: "TDD",
        labelKo: "기술실사",
        description: "Technical Due Diligence",
        status: "coming_soon",
        icon: Monitor,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
    ],
  },
  {
    id: "checklists",
    label: "Checklist & Timeline",
    labelKo: "체크리스트 & 타임라인",
    description: "Closing 체크리스트와 딜 타임라인을 관리합니다",
    icon: ClipboardCheck,
    colorCls: "text-text-secondary",
    bgCls: "bg-gray-100",
    subTypes: [
      {
        id: "closing_checklist",
        label: "Closing Checklist",
        labelKo: "Closing 체크리스트",
        description: "거래 종결 조건 및 요구사항 관리",
        status: "requires_context",
        createPath: "/ma/transactions",
        icon: ListChecks,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
      {
        id: "deal_checklist",
        label: "Deal Checklist & Timeline",
        labelKo: "딜 체크리스트 & 타임라인",
        description: "거래 주요 일정 및 마일스톤 관리",
        status: "requires_context",
        createPath: "/ma/transactions",
        icon: CalendarClock,
        colorCls: "text-text-secondary",
        bgCls: "bg-gray-50",
      },
    ],
  },
];
