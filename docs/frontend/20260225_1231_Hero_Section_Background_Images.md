# 히어로 섹션 배경 이미지 적용

> 작성: 2026-02-25 12:31

## 개요

모든 PageHero 컴포넌트에 배경 이미지를 추가하여 시각적 풍부함을 강화했다. 기존 짙은 녹색 그라데이션(`hero-gradient-radial`) 위에 낮은 opacity로 겹쳐 은은한 텍스처 효과를 준다.

## 변경 사항

### PageHero 컴포넌트 수정
- **파일**: `amic-platform/src/components/ui/PageHero.tsx`
- `object-top` 추가 — 이미지 상단(나무 빽빽한 부분)이 보이도록 조정
- `backgroundOpacity` 기본값 `0.2` 유지

### 대시보드 히어로
- **파일**: `amic-platform/src/pages/DashboardPage.tsx`
- 이미지: `forest-cover.jpg` (기존 유지)
- `backgroundOpacity={0.4}` (0.15 → 0.4로 상향, 포레스트 이미지 선명도 강화)

### 이미지 소스 (총 17장)

#### 건축 사진 (11장) → `assets/images/heroes/`
| 파일명 | 설명 |
|--------|------|
| `hero-arch-teal.jpg` | 청록 각진 건물 |
| `hero-arch-mono.jpg` | 흑백 곡선 건물 |
| `hero-arch-silver.jpg` | 은색 건물 + 하늘 |
| `hero-arch-wave.jpg` | 청록 웨이브 건물 |
| `hero-arch-diamond.jpg` | 은색 다이아몬드 패턴 |
| `hero-arch-blue-wave.jpg` | 파란 추상 웨이브 |
| `hero-arch-dark-round.jpg` | 다크 라운드 건물 |
| `hero-arch-white-round.jpg` | 흰 원형 건물 |
| `hero-arch-purple.jpg` | 퍼플 각진 건물 |
| `hero-arch-dome.jpg` | 핑크-틸 돔 |
| `hero-arch-symmetry.jpg` | 실내 대칭 구조 |

#### 숲/자연 사진 (6장) → `assets/images/heroes/` + `assets/images/`
| 파일명 | 설명 | 소스 |
|--------|------|------|
| `forest-bg.jpg` | 안개 낀 녹색 산림 | 기존 assets |
| `forestgp-background.jpg` | 가을 숲 파노라마 | forestgp.com |
| `forestgp-forest.jpg` | 짙은 녹색 침엽수+안개 | forestgp.com |
| `forestgp-news.jpg` | 침엽수 잎 매크로 | forestgp.com |
| `forestgp-vc.jpg` | 나무 캐노피 올려다봄 | forestgp.com |
| `forestgp-nature.jpg` | 숲 속 도로+산 | forestgp.com |

## 모듈별 이미지 배분 (52페이지)

### MA 모듈 (3페이지) — 건축
| 페이지 | 이미지 |
|--------|--------|
| TransactionListPage | `hero-arch-teal.jpg` |
| TransactionWorkspacePage | `hero-arch-dark-round.jpg` |
| CreateTransactionPage | `hero-arch-blue-wave.jpg` |

### FDD 모듈 (13페이지) — 건축
| 페이지 | 이미지 |
|--------|--------|
| DealListPage | `hero-arch-silver.jpg` |
| DealSetupPage | `hero-arch-dome.jpg` |
| DealSetupWizardPage | `hero-arch-dome.jpg` |
| WorkflowOverviewPage | `hero-arch-diamond.jpg` |
| MappingPage | `hero-arch-purple.jpg` |
| DefinitionPage | `hero-arch-symmetry.jpg` |
| IssuesPage | `hero-arch-wave.jpg` |
| QoEPage | `hero-arch-white-round.jpg` |
| NWCPage | `hero-arch-blue-wave.jpg` |
| NetDebtPage | `hero-arch-mono.jpg` |
| ReportPage | `hero-arch-teal.jpg` |
| UploadPage | `hero-arch-dark-round.jpg` |
| VdrPage | `hero-arch-diamond.jpg` |

### KIIS 모듈 (19페이지) — 숲/자연 (Forest GP 브랜딩)
| 페이지 | 이미지 |
|--------|--------|
| DashboardPage (KIIS) | `forestgp-forest.jpg` |
| GPListPage | `forestgp-vc.jpg` |
| GPDetailPage | `forestgp-news.jpg` |
| ManagerListPage | `forestgp-background.jpg` |
| ManagerProfilePage | `forestgp-nature.jpg` |
| CompanyListPage | `forest-bg.jpg` |
| CompanyDetailPage | `forestgp-forest.jpg` |
| FundListPage | `forestgp-vc.jpg` |
| FundDetailPage | `forestgp-news.jpg` |
| ReitListPage | `forestgp-background.jpg` |
| ReitDetailPage | `forestgp-nature.jpg` |
| WatchlistPage | `forest-bg.jpg` |
| DealSourcingPage | `forestgp-forest.jpg` |
| SanctionListPage | `forestgp-nature.jpg` |
| EntityResolutionPage | `forestgp-background.jpg` |
| DisclosurePage | `forestgp-vc.jpg` |
| PortfolioPage | `forestgp-news.jpg` |
| NewsListPage | `forest-bg.jpg` |
| NewsDetailPage | `forestgp-forest.jpg` |

### Docs/IM + Platform (17페이지) — 건축+숲 혼합
| 페이지 | 이미지 |
|--------|--------|
| StudioHomePage | `hero-arch-symmetry.jpg` |
| TemplatesPage (docs) | `hero-arch-teal.jpg` |
| TemplatesPage (im) | `hero-arch-purple.jpg` |
| DocumentDetailPage (docs) | `forestgp-forest.jpg` |
| DocumentDetailPage (im) | `forestgp-vc.jpg` |
| DocumentListPage (im) | `hero-arch-wave.jpg` |
| CreateDocumentPage (docs) | `hero-arch-silver.jpg` |
| CreateDocumentPage (im) | `hero-arch-mono.jpg` |
| CreateLegalDocumentPage | `hero-arch-dark-round.jpg` |
| CreateLDDReportPage | `hero-arch-white-round.jpg` |
| CategoryDocumentsPage | `hero-arch-dome.jpg` |
| VdrOverviewPage | `forestgp-nature.jpg` |
| HelpPage | `forest-bg.jpg` |
| CalendarPage | `forestgp-background.jpg` |
| AnalyticsPage | `hero-arch-diamond.jpg` |
| ExportsPage | `hero-arch-blue-wave.jpg` |
| TeamPage | `forest-bg.jpg` |

## 기술 세부사항

- 모든 페이지: `backgroundOpacity={0.18}` (대시보드 제외)
- 대시보드: `backgroundOpacity={0.4}` + `forest-cover.jpg`
- PageHero `<img>`: `object-cover object-top` — 이미지 상단 기준 크롭
- 빌드 검증: 14.59s 성공
