import { useState } from "react";

const stages = [
  {
    id: 1,
    name: "수임 및 전략 수립",
    weeks: "1~4주차",
    icon: "🤝",
    color: "#1a1a2e",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "고객 발굴 및 관계 관리", deliverable: "리드 파이프라인", auto: "semi", role: "대표/MD" },
        { name: "뷰티 콘테스트/피치북 작성", deliverable: "피치북", auto: "full", role: "딜팀" },
        { name: "수임계약서 체결", deliverable: "Engagement Letter", auto: "semi", role: "대표/법률팀" },
        { name: "이해충돌 심사", deliverable: "Conflict Clearance", auto: "full", role: "컴플라이언스" },
        { name: "딜팀 구성 및 WGL 생성", deliverable: "Working Group List", auto: "full", role: "PM" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "인수 전략 정의", deliverable: "전략 문서", auto: "manual", role: "고객/자문사" },
        { name: "인수 기준 설정 (산업/규모/지역)", deliverable: "기준 스코어카드", auto: "semi", role: "딜팀" },
        { name: "예산 및 자금조달 매개변수 설정", deliverable: "자금계획서", auto: "manual", role: "CFO/자문사" },
        { name: "자문사 선임 및 수임계약", deliverable: "Engagement Letter", auto: "semi", role: "대표" },
        { name: "이사회/투자위원회 승인", deliverable: "승인 기록", auto: "manual", role: "이사회", gate: true },
      ],
    },
    integration: null,
  },
  {
    id: 2,
    name: "준비 및 대상 개발",
    weeks: "3~10주차",
    icon: "📋",
    color: "#16213e",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "재무제표 정규화 (3~5년)", deliverable: "정규화 재무제표", auto: "semi", role: "회계팀" },
        { name: "QoE 분석 의뢰 및 수행", deliverable: "QoE 보고서", auto: "semi", role: "회계법인" },
        { name: "종합 재무 모델 구축 (DCF/Comps/LBO)", deliverable: "재무 모델", auto: "semi", role: "애널리스트" },
        { name: "CIM 작성 (50~100p)", deliverable: "CIM", auto: "full", role: "딜팀" },
        { name: "익명 티저 생성", deliverable: "블라인드 티저", auto: "full", role: "딜팀" },
        { name: "VDR 구축 및 문서 분류", deliverable: "데이터룸", auto: "full", role: "PM/법률팀" },
        { name: "잠재 매수자 유니버스 매핑", deliverable: "매수자 리스트 (50~200+)", auto: "semi", role: "딜팀" },
        { name: "NDA 템플릿 준비", deliverable: "NDA 양식", auto: "full", role: "법률팀" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "타겟 롱리스트 구축 (50~200개)", deliverable: "롱리스트", auto: "semi", role: "딜팀" },
        { name: "재무/전략/정성 기준 스크리닝", deliverable: "스크리닝 결과", auto: "full", role: "애널리스트" },
        { name: "숏리스트 선정 (10~20개)", deliverable: "숏리스트", auto: "semi", role: "딜팀" },
        { name: "우선순위 리스트 (3~5개)", deliverable: "우선순위 리스트", auto: "semi", role: "고객/딜팀" },
        { name: "타겟 프로필 작성 (1~2p)", deliverable: "타겟 프로필", auto: "full", role: "애널리스트" },
        { name: "동적 재순위화 시스템", deliverable: "갱신된 순위", auto: "full", role: "시스템" },
      ],
    },
    integration: null,
  },
  {
    id: 3,
    name: "마케팅 및 초기 접근",
    weeks: "8~14주차",
    icon: "📨",
    color: "#0f3460",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "단계별 티저 발송 (고우선순위→확대)", deliverable: "발송 로그", auto: "full", role: "PM" },
        { name: "NDA 체결 및 추적", deliverable: "체결된 NDA", auto: "full", role: "법률팀" },
        { name: "CIM 배포 (NDA 확인 후)", deliverable: "배포 로그", auto: "full", role: "PM" },
        { name: "프로세스 레터 발송", deliverable: "프로세스 레터", auto: "semi", role: "딜팀" },
        { name: "매수자 참여도 추적 (VDR 분석)", deliverable: "참여 분석 대시보드", auto: "full", role: "시스템" },
        { name: "FAQ 문서 관리", deliverable: "FAQ 문서", auto: "semi", role: "딜팀" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "타겟 초기 접촉 (CEO급/중개인)", deliverable: "접촉 로그", auto: "semi", role: "대표/딜팀" },
        { name: "NDA 협상 및 체결", deliverable: "체결된 NDA", auto: "semi", role: "법률팀" },
        { name: "예비 정보 검토", deliverable: "검토 메모", auto: "manual", role: "딜팀" },
        { name: "초기 재무 모델 및 밸류에이션", deliverable: "예비 밸류에이션", auto: "semi", role: "애널리스트" },
        { name: "전략적 적합성 평가", deliverable: "적합성 스코어카드", auto: "semi", role: "딜팀" },
        { name: "IOI 작성 및 제출", deliverable: "IOI 서한", auto: "semi", role: "딜팀", gate: true },
      ],
    },
    integration: { name: "🔗 NDA 게이트웨이", desc: "NDA 체결 시 매수자의 기밀자료 접근 해제" },
  },
  {
    id: 4,
    name: "입찰 관리 및 실사",
    weeks: "12~24주차",
    icon: "🔍",
    color: "#533483",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "1라운드: IOI 수집 및 비교 매트릭스", deliverable: "IOI 비교표", auto: "full", role: "딜팀" },
        { name: "매수자 숏리스팅 (3~6명)", deliverable: "숏리스트", auto: "semi", role: "대표/고객" },
        { name: "경영진 프레젠테이션 주관", deliverable: "MP 자료/평가", auto: "manual", role: "딜팀/고객" },
        { name: "2라운드: LOI 수집 및 평가", deliverable: "LOI 비교표", auto: "full", role: "딜팀" },
        { name: "VDR 활동 기반 입찰자 스코어링", deliverable: "참여도 점수", auto: "full", role: "시스템" },
        { name: "Q&A 관리 (중개자 역할)", deliverable: "Q&A 로그", auto: "semi", role: "딜팀/법률팀" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "9개 실사 워크스트림 조율", deliverable: "실사 보고서", auto: "semi", role: "딜팀 전체" },
        { name: "AI 계약 분석 (1,400+ 필드)", deliverable: "계약 분석 결과", auto: "full", role: "법률팀/AI" },
        { name: "DCF/Comps/선례거래 밸류에이션", deliverable: "밸류에이션 요약", auto: "semi", role: "애널리스트" },
        { name: "시너지 분석 (비용/매출)", deliverable: "시너지 모델", auto: "semi", role: "딜팀" },
        { name: "딜 구조 결정 (자산/주식/합병)", deliverable: "구조 추천 메모", auto: "manual", role: "법률팀" },
        { name: "LOI/텀시트 제출", deliverable: "LOI", auto: "semi", role: "딜팀", gate: true },
      ],
    },
    integration: { name: "🔗 IOI/LOI 브릿지 + VDR 상호작용 + 경영진 PT", desc: "매수→매도 입찰 연동, Q&A 실시간 소통" },
  },
  {
    id: 5,
    name: "협상 및 문서화",
    weeks: "20~30주차",
    icon: "⚖️",
    color: "#e94560",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "SPA 초안 검토 및 수정", deliverable: "SPA 마크업", auto: "semi", role: "법률팀" },
        { name: "진술 및 보증(R&W) 협상", deliverable: "R&W 추적표", auto: "semi", role: "법률팀" },
        { name: "매매대금 메커니즘 협상", deliverable: "가격 메모", auto: "manual", role: "딜팀/법률팀" },
        { name: "공시 일정(Disclosure Schedules) 작성", deliverable: "공시 일정", auto: "semi", role: "법률팀" },
        { name: "규제 승인 신고 (HSR/CFIUS 등)", deliverable: "신고 서류", auto: "semi", role: "법률팀" },
        { name: "부속 계약 협상 (TSA/경업금지 등)", deliverable: "부속 계약", auto: "semi", role: "법률팀" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "SPA 초안 작성", deliverable: "SPA 초안", auto: "semi", role: "법률팀" },
        { name: "R&W 범위 및 손해배상 구조 설계", deliverable: "R&W 제안서", auto: "semi", role: "법률팀" },
        { name: "어닝아웃/에스크로 조건 설정", deliverable: "에스크로 계약", auto: "manual", role: "딜팀" },
        { name: "RWI(진술보증보험) 가입 검토", deliverable: "RWI 견적", auto: "semi", role: "보험팀" },
        { name: "규제 승인 공동 신고", deliverable: "공동 신고 서류", auto: "semi", role: "법률팀" },
        { name: "자금조달 확약서 확보", deliverable: "Commitment Letter", auto: "manual", role: "재무팀", gate: true },
      ],
    },
    integration: { name: "🔗 SPA 협상 수렴 + 규제 조율", desc: "양측 법률팀 동일 문서 듀얼 트랙 레드라인" },
  },
  {
    id: 6,
    name: "클로징",
    weeks: "28~36주차",
    icon: "✅",
    color: "#0a9396",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "선행조건 충족 확인", deliverable: "체크리스트 (녹/적)", auto: "full", role: "법률팀" },
        { name: "클로징 문서 서명 (전자서명)", deliverable: "체결 문서", auto: "full", role: "법률팀" },
        { name: "송금 확인 및 소유권 이전", deliverable: "송금 확인서", auto: "semi", role: "재무팀" },
        { name: "클로징 바인더 자동 편찬", deliverable: "클로징 바인더", auto: "full", role: "법률팀/시스템" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "자금 흐름표 작성 및 확인", deliverable: "Funds Flow Memo", auto: "full", role: "재무팀" },
        { name: "선행조건 충족 확인", deliverable: "체크리스트 (녹/적)", auto: "full", role: "법률팀" },
        { name: "클로징 문서 서명 (전자서명)", deliverable: "체결 문서", auto: "full", role: "법률팀" },
        { name: "송금 실행", deliverable: "송금 기록", auto: "semi", role: "재무팀", gate: true },
      ],
    },
    integration: { name: "🔗 클로징 동기화", desc: "양측 조건 동시 충족, 통합 클로징 대시보드" },
  },
  {
    id: 7,
    name: "클로징 후 및 통합",
    weeks: "36~88주차+",
    icon: "🔄",
    color: "#005f73",
    sellSide: {
      title: "매도자문 (Sell-side)",
      tasks: [
        { name: "운전자본 정산 (90~120일)", deliverable: "정산 계산서", auto: "full", role: "회계팀" },
        { name: "어닝아웃 KPI 모니터링", deliverable: "KPI 대시보드", auto: "full", role: "딜팀" },
        { name: "에스크로 클레임 관리", deliverable: "클레임 로그", auto: "semi", role: "법률팀" },
        { name: "PPA(매매대금 배분) 지원", deliverable: "PPA 보고서", auto: "semi", role: "회계팀" },
      ],
    },
    buySide: {
      title: "매수자문 (Buy-side)",
      tasks: [
        { name: "PMI 통합관리사무소(IMO) 설립", deliverable: "IMO 계획서", auto: "semi", role: "프로젝트팀" },
        { name: "Day 1 실행 (공지/연속성)", deliverable: "Day 1 체크리스트", auto: "semi", role: "딜팀 전체" },
        { name: "6개 기능별 통합 워크스트림 추적", deliverable: "통합 대시보드", auto: "full", role: "IMO" },
        { name: "시너지 스코어카드 (비용/매출)", deliverable: "주간 시너지 보고", auto: "full", role: "딜팀" },
      ],
    },
    integration: null,
  },
];

const autoLabels = { full: "완전 자동", semi: "반자동", manual: "수동" };
const autoColors = { full: "#f59e0b", semi: "#6366f1", manual: "#94a3b8" };

export default function AMICWorkflow() {
  const [expandedStage, setExpandedStage] = useState(null);
  const [hoveredTask, setHoveredTask] = useState(null);
  const [viewMode, setViewMode] = useState("overview");

  const toggleStage = (id) => {
    setExpandedStage(expandedStage === id ? null : id);
  };

  const totalTasks = stages.reduce(
    (acc, s) => acc + s.sellSide.tasks.length + s.buySide.tasks.length,
    0
  );
  const autoTasks = stages.reduce(
    (acc, s) =>
      acc +
      [...s.sellSide.tasks, ...s.buySide.tasks].filter(
        (t) => t.auto === "full"
      ).length,
    0
  );
  const semiTasks = stages.reduce(
    (acc, s) =>
      acc +
      [...s.sellSide.tasks, ...s.buySide.tasks].filter(
        (t) => t.auto === "semi"
      ).length,
    0
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0b0b1a 0%, #1a1a2e 50%, #0f3460 100%)",
        color: "#e0e0e0",
        fontFamily: "'Noto Sans KR', 'Pretendard', -apple-system, sans-serif",
        padding: "24px 16px",
      }}
    >
      {/* Header */}
      <div style={{ maxWidth: 1200, margin: "0 auto 32px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 8,
          }}
        >
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "linear-gradient(135deg, #e94560, #533483)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
              fontWeight: 700,
              color: "#fff",
              letterSpacing: -1,
            }}
          >
            A
          </div>
          <div>
            <h1
              style={{
                fontSize: 28,
                fontWeight: 800,
                margin: 0,
                background: "linear-gradient(90deg, #fff, #94a3b8)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                letterSpacing: -0.5,
              }}
            >
              AMIC Platform
            </h1>
            <p style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>
              M&A 자문사 통합 워크플로우 · Sell-side & Buy-side
            </p>
          </div>
        </div>

        {/* Stats Bar */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginTop: 20,
            flexWrap: "wrap",
          }}
        >
          {[
            { label: "총 단계", value: "7", color: "#e94560" },
            { label: "세부 업무", value: totalTasks, color: "#533483" },
            { label: "완전 자동", value: autoTasks, color: "#f59e0b" },
            { label: "반자동", value: semiTasks, color: "#6366f1" },
            { label: "연계 포인트", value: "5", color: "#0a9396" },
          ].map((stat, i) => (
            <div
              key={i}
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 10,
                padding: "10px 16px",
                minWidth: 100,
                flex: 1,
              }}
            >
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  color: stat.color,
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 11, color: "#94a3b8" }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>

        {/* View Toggle */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginTop: 16,
          }}
        >
          {[
            { id: "overview", label: "전체 개요" },
            { id: "detail", label: "상세 보기" },
          ].map((v) => (
            <button
              key={v.id}
              onClick={() => {
                setViewMode(v.id);
                setExpandedStage(v.id === "detail" ? 1 : null);
              }}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                border: "1px solid",
                borderColor:
                  viewMode === v.id
                    ? "#e94560"
                    : "rgba(255,255,255,0.1)",
                background:
                  viewMode === v.id
                    ? "rgba(233,69,96,0.15)"
                    : "transparent",
                color: viewMode === v.id ? "#e94560" : "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
                transition: "all 0.2s",
              }}
            >
              {v.label}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div
          style={{
            display: "flex",
            gap: 16,
            marginTop: 16,
            flexWrap: "wrap",
            fontSize: 12,
          }}
        >
          {[
            { color: "#3b82f6", label: "매도자문 (Sell-side)" },
            { color: "#10b981", label: "매수자문 (Buy-side)" },
            { color: "#a855f7", label: "연계 포인트" },
            { color: "#f59e0b", label: "● 완전 자동" },
            { color: "#6366f1", label: "● 반자동" },
            { color: "#94a3b8", label: "● 수동" },
            { color: "#ef4444", label: "▸ 게이팅 마일스톤" },
          ].map((item, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: item.label.startsWith("●") || item.label.startsWith("▸") ? "50%" : 3,
                  background: item.color,
                }}
              />
              <span style={{ color: "#94a3b8" }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Stages */}
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        {stages.map((stage, si) => {
          const isExpanded = expandedStage === stage.id;
          return (
            <div key={stage.id} style={{ marginBottom: 12 }}>
              {/* Stage Header */}
              <button
                onClick={() => toggleStage(stage.id)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "16px 20px",
                  background: isExpanded
                    ? `linear-gradient(135deg, ${stage.color}cc, ${stage.color}88)`
                    : "rgba(255,255,255,0.04)",
                  border: `1px solid ${isExpanded ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: isExpanded ? "14px 14px 0 0" : 14,
                  color: "#fff",
                  cursor: "pointer",
                  transition: "all 0.3s ease",
                  textAlign: "left",
                }}
              >
                <span style={{ fontSize: 28 }}>{stage.icon}</span>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 17,
                      fontWeight: 700,
                      letterSpacing: -0.3,
                    }}
                  >
                    <span
                      style={{
                        display: "inline-block",
                        background: "rgba(255,255,255,0.15)",
                        borderRadius: 6,
                        padding: "2px 8px",
                        fontSize: 12,
                        fontWeight: 600,
                        marginRight: 8,
                      }}
                    >
                      {stage.id}단계
                    </span>
                    {stage.name}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "rgba(255,255,255,0.5)",
                      marginTop: 2,
                    }}
                  >
                    {stage.weeks} · 매도 {stage.sellSide.tasks.length}개 + 매수{" "}
                    {stage.buySide.tasks.length}개 업무
                  </div>
                </div>
                {stage.integration && (
                  <div
                    style={{
                      background: "rgba(168,85,247,0.2)",
                      border: "1px solid rgba(168,85,247,0.4)",
                      borderRadius: 8,
                      padding: "4px 10px",
                      fontSize: 11,
                      color: "#c084fc",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {stage.integration.name}
                  </div>
                )}
                <span
                  style={{
                    fontSize: 18,
                    transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.3s",
                    color: "rgba(255,255,255,0.4)",
                  }}
                >
                  ▼
                </span>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div
                  style={{
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderTop: "none",
                    borderRadius: "0 0 14px 14px",
                    padding: 16,
                  }}
                >
                  {/* Integration Banner */}
                  {stage.integration && (
                    <div
                      style={{
                        background:
                          "linear-gradient(90deg, rgba(168,85,247,0.12), rgba(168,85,247,0.04))",
                        border: "1px solid rgba(168,85,247,0.25)",
                        borderRadius: 10,
                        padding: "10px 16px",
                        marginBottom: 16,
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                      }}
                    >
                      <span style={{ fontSize: 20 }}>🔗</span>
                      <div>
                        <div
                          style={{
                            fontSize: 13,
                            fontWeight: 700,
                            color: "#c084fc",
                          }}
                        >
                          연계 포인트: {stage.integration.name.replace("🔗 ", "")}
                        </div>
                        <div style={{ fontSize: 11, color: "#94a3b8" }}>
                          {stage.integration.desc}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Dual Track */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 12,
                    }}
                  >
                    {/* Sell-side */}
                    <div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: "#60a5fa",
                          marginBottom: 8,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        <div
                          style={{
                            width: 4,
                            height: 16,
                            borderRadius: 2,
                            background: "#3b82f6",
                          }}
                        />
                        {stage.sellSide.title}
                      </div>
                      {stage.sellSide.tasks.map((task, ti) => (
                        <div
                          key={ti}
                          onMouseEnter={() =>
                            setHoveredTask(`s-${stage.id}-${ti}`)
                          }
                          onMouseLeave={() => setHoveredTask(null)}
                          style={{
                            background:
                              hoveredTask === `s-${stage.id}-${ti}`
                                ? "rgba(59,130,246,0.1)"
                                : "rgba(255,255,255,0.02)",
                            border: `1px solid ${task.gate ? "rgba(239,68,68,0.4)" : "rgba(255,255,255,0.05)"}`,
                            borderRadius: 8,
                            padding: "8px 12px",
                            marginBottom: 6,
                            transition: "all 0.2s",
                            cursor: "default",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "flex-start",
                              gap: 8,
                            }}
                          >
                            <div
                              style={{
                                width: 7,
                                height: 7,
                                borderRadius: "50%",
                                background: autoColors[task.auto],
                                marginTop: 5,
                                flexShrink: 0,
                              }}
                            />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div
                                style={{
                                  fontSize: 12,
                                  fontWeight: 600,
                                  color: "#e0e0e0",
                                  lineHeight: 1.4,
                                }}
                              >
                                {task.gate && (
                                  <span
                                    style={{
                                      color: "#ef4444",
                                      marginRight: 4,
                                      fontSize: 10,
                                    }}
                                  >
                                    🚩
                                  </span>
                                )}
                                {task.name}
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  gap: 6,
                                  marginTop: 4,
                                  flexWrap: "wrap",
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: 10,
                                    background: "rgba(255,255,255,0.06)",
                                    padding: "1px 6px",
                                    borderRadius: 4,
                                    color: "#94a3b8",
                                  }}
                                >
                                  📄 {task.deliverable}
                                </span>
                                <span
                                  style={{
                                    fontSize: 10,
                                    background: `${autoColors[task.auto]}22`,
                                    color: autoColors[task.auto],
                                    padding: "1px 6px",
                                    borderRadius: 4,
                                    fontWeight: 600,
                                  }}
                                >
                                  {autoLabels[task.auto]}
                                </span>
                                <span
                                  style={{
                                    fontSize: 10,
                                    color: "#64748b",
                                  }}
                                >
                                  👤 {task.role}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Buy-side */}
                    <div>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: "#34d399",
                          marginBottom: 8,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        <div
                          style={{
                            width: 4,
                            height: 16,
                            borderRadius: 2,
                            background: "#10b981",
                          }}
                        />
                        {stage.buySide.title}
                      </div>
                      {stage.buySide.tasks.map((task, ti) => (
                        <div
                          key={ti}
                          onMouseEnter={() =>
                            setHoveredTask(`b-${stage.id}-${ti}`)
                          }
                          onMouseLeave={() => setHoveredTask(null)}
                          style={{
                            background:
                              hoveredTask === `b-${stage.id}-${ti}`
                                ? "rgba(16,185,129,0.1)"
                                : "rgba(255,255,255,0.02)",
                            border: `1px solid ${task.gate ? "rgba(239,68,68,0.4)" : "rgba(255,255,255,0.05)"}`,
                            borderRadius: 8,
                            padding: "8px 12px",
                            marginBottom: 6,
                            transition: "all 0.2s",
                            cursor: "default",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "flex-start",
                              gap: 8,
                            }}
                          >
                            <div
                              style={{
                                width: 7,
                                height: 7,
                                borderRadius: "50%",
                                background: autoColors[task.auto],
                                marginTop: 5,
                                flexShrink: 0,
                              }}
                            />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div
                                style={{
                                  fontSize: 12,
                                  fontWeight: 600,
                                  color: "#e0e0e0",
                                  lineHeight: 1.4,
                                }}
                              >
                                {task.gate && (
                                  <span
                                    style={{
                                      color: "#ef4444",
                                      marginRight: 4,
                                      fontSize: 10,
                                    }}
                                  >
                                    🚩
                                  </span>
                                )}
                                {task.name}
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  gap: 6,
                                  marginTop: 4,
                                  flexWrap: "wrap",
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: 10,
                                    background: "rgba(255,255,255,0.06)",
                                    padding: "1px 6px",
                                    borderRadius: 4,
                                    color: "#94a3b8",
                                  }}
                                >
                                  📄 {task.deliverable}
                                </span>
                                <span
                                  style={{
                                    fontSize: 10,
                                    background: `${autoColors[task.auto]}22`,
                                    color: autoColors[task.auto],
                                    padding: "1px 6px",
                                    borderRadius: 4,
                                    fontWeight: 600,
                                  }}
                                >
                                  {autoLabels[task.auto]}
                                </span>
                                <span
                                  style={{
                                    fontSize: 10,
                                    color: "#64748b",
                                  }}
                                >
                                  👤 {task.role}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Connector Arrow */}
              {si < stages.length - 1 && !isExpanded && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    padding: "4px 0",
                  }}
                >
                  <div
                    style={{
                      width: 2,
                      height: 12,
                      background:
                        "linear-gradient(to bottom, rgba(255,255,255,0.15), rgba(255,255,255,0.05))",
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          maxWidth: 1200,
          margin: "32px auto 0",
          padding: "16px 20px",
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12,
          fontSize: 11,
          color: "#64748b",
          textAlign: "center",
        }}
      >
        AMIC Platform M&A 자문사 워크플로우 설계 · DealRoom.net, Datasite, Ansarada, Midaxo 참조 ·{" "}
        매도자문(Sell-side) + 매수자문(Buy-side) 7단계 병렬 아키텍처 · {totalTasks}개 세부 업무 · 5개 연계 포인트
      </div>
    </div>
  );
}
