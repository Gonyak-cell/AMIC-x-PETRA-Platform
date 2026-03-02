// ── Team Members (InlineCombobox용) ─────────────────
export interface TeamMember {
  email: string;
  name: string;
  title: string;
}

export const TEAM_MEMBERS: TeamMember[] = [
  { email: "ytkim@amic.kr", name: "김양태", title: "대표 / 회계사" },
  { email: "jwsuh@amic.kr", name: "서지원", title: "변호사" },
  { email: "yhlim@amic.kr", name: "임영훈", title: "변호사" },
  { email: "bj.park@amic.kr", name: "박병준", title: "변호사" },
  { email: "wsjo@amic.kr", name: "조우상", title: "이사" },
  { email: "tryoon@amic.kr", name: "윤태리", title: "실장" },
];
