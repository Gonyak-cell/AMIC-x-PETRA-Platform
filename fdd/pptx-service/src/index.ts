import express, { Request, Response } from "express";
import PptxGenJS from "pptxgenjs";

const app = express();
const PORT = process.env.PORT || 3100;

app.use(express.json({ limit: "50mb" }));

// =============================================================================
// Types
// =============================================================================

interface Position {
  x: number;
  y: number;
}

interface Size {
  w: number;
  h: number;
}

interface KPIItem {
  label: string;
  value: string;
  unit?: string;
  trend?: "up" | "down" | "flat";
}

interface TableColumn {
  key: string;
  header: string;
  width?: number;
  align?: "left" | "center" | "right";
  format?: string;
}

interface ChartData {
  categories: string[];
  values: (string | number | null)[];
  series_name?: string;
}

interface CoverBlock {
  type: "cover";
  deal_name: string;
  deal_type?: string;
  target_name?: string;
  date?: string;
  prepared_by?: string;
  confidentiality?: string;
  logo_base64?: string;
  position?: Position;
}

interface KPIBlock {
  type: "kpi";
  title: string;
  kpis: KPIItem[];
  columns?: number;
  position?: Position;
  size?: Size;
}

interface TableBlock {
  type: "table";
  title: string;
  columns: TableColumn[];
  rows: Record<string, unknown>[];
  footer_rows?: Record<string, unknown>[];
  show_header?: boolean;
  zebra_stripe?: boolean;
  position?: Position;
  size?: Size;
  max_rows_per_slide?: number; // 슬라이드당 최대 행 수 (오버플로우 처리)
}

interface ChartBlock {
  type: "chart";
  chart_type: "waterfall" | "bar" | "line" | "pie";
  title: string;
  data?: ChartData;
  image_base64?: string;
  position?: Position;
  size?: Size;
}

interface TextBlock {
  type: "text";
  title?: string;
  content: string;
  bullet_points?: string[];
  risk_level?: "high" | "medium" | "low";
  highlight?: boolean;
  position?: Position;
  size?: Size;
}

interface EvidenceRef {
  evidence_id: string;
  source_type: string;
  source_id: string;
  description?: string;
}

interface ClaimBlock {
  type: "claim";
  claim_text: string;
  evidence_refs: EvidenceRef[];
  verified: boolean;
  risk_level?: "high" | "medium" | "low";
  category?: string;
  position?: Position;
  size?: Size;
}

interface IssueItem {
  issue_id: string;
  category: string;
  severity: string;
  title: string;
  description?: string;
  status: string;
  recommendation?: string;
}

interface IssueBlock {
  type: "issue";
  title: string;
  issues: IssueItem[];
  show_resolved?: boolean;
  position?: Position;
  size?: Size;
}

interface MethodologyItem {
  step: number;
  title: string;
  description?: string;
}

interface MethodologyBlock {
  type: "methodology";
  title: string;
  introduction?: string;
  steps: MethodologyItem[];
  limitations?: string[];
  position?: Position;
  size?: Size;
}

interface ScopeItem {
  category: string;
  label: string;
  value: string;
}

interface ScopeBlock {
  type: "scope";
  title: string;
  scope_items: ScopeItem[];
  definitions?: Record<string, string>;
  position?: Position;
  size?: Size;
}

interface AppendixItem {
  title: string;
  content?: string;
  table_data?: Record<string, unknown>[];
  reference_page?: number;
}

interface AppendixBlock {
  type: "appendix";
  title: string;
  items: AppendixItem[];
  position?: Position;
  size?: Size;
}

type ReportBlock = CoverBlock | KPIBlock | TableBlock | ChartBlock | TextBlock | ClaimBlock | IssueBlock | MethodologyBlock | ScopeBlock | AppendixBlock;

interface ReportMetadata {
  deal_id: string;
  deal_name: string;
  generated_at?: string;
  version?: string;
}

interface ReportSchema {
  meta: ReportMetadata;
  sections: ReportBlock[];
  design_system?: DesignSystem;
}

interface DesignSystemColors {
  primary: string;
  secondary: string;
  positive: string;
  negative: string;
  neutral: string;
  header_bg: string;
  header_text: string;
  alt_row: string;
}

interface DesignSystemFonts {
  heading: string;
  body: string;
  data: string;
}

interface DesignSystemSizes {
  slide_title: number;
  section_title: number;
  body: number;
  table_header: number;
  table_body: number;
}

interface DesignSystem {
  colors?: Partial<DesignSystemColors>;
  fonts?: Partial<DesignSystemFonts>;
  sizes?: Partial<DesignSystemSizes>;
}

interface ResolvedDesignSystem {
  colors: DesignSystemColors;
  fonts: DesignSystemFonts;
  sizes: DesignSystemSizes;
}

// =============================================================================
// Default Design System
// =============================================================================

const DEFAULT_DESIGN: ResolvedDesignSystem = {
  colors: {
    primary: "#003366",
    secondary: "#0066CC",
    positive: "#2E7D32",
    negative: "#E0301E",
    neutral: "#666666",
    header_bg: "#003366",
    header_text: "#FFFFFF",
    alt_row: "#F5F5F5",
  },
  fonts: {
    heading: "맑은 고딕",
    body: "맑은 고딕",
    data: "Calibri",
  },
  sizes: {
    slide_title: 28,
    section_title: 24,
    body: 14,
    table_header: 11,
    table_body: 10,
  },
};

// =============================================================================
// Render Functions
// =============================================================================

function renderCoverSlide(
  pptx: PptxGenJS,
  block: CoverBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();
  slide.background = { color: design.colors.primary };

  // Deal Name (main title)
  slide.addText(block.deal_name || "Untitled Deal", {
    x: 0.5,
    y: 2.0,
    w: 9.0,
    h: 1.0,
    fontSize: 36,
    fontFace: design.fonts.heading,
    color: "FFFFFF",
    bold: true,
    align: "center",
  });

  // Target Name
  if (block.target_name) {
    slide.addText(block.target_name, {
      x: 0.5,
      y: 3.0,
      w: 9.0,
      h: 0.5,
      fontSize: 24,
      fontFace: design.fonts.body,
      color: "FFFFFF",
      align: "center",
    });
  }

  // Deal Type
  if (block.deal_type) {
    slide.addText(block.deal_type, {
      x: 0.5,
      y: 3.5,
      w: 9.0,
      h: 0.4,
      fontSize: 18,
      fontFace: design.fonts.body,
      color: "CCCCCC",
      align: "center",
    });
  }

  // Date and Confidentiality (footer)
  const footerParts: string[] = [];
  if (block.date) footerParts.push(block.date);
  if (block.confidentiality) footerParts.push(block.confidentiality);

  if (footerParts.length > 0) {
    slide.addText(footerParts.join(" | "), {
      x: 0.5,
      y: 5.0,
      w: 9.0,
      h: 0.3,
      fontSize: 12,
      fontFace: design.fonts.body,
      color: "999999",
      align: "center",
    });
  }

  // Logo (if provided)
  if (block.logo_base64) {
    slide.addImage({
      data: `data:image/png;base64,${block.logo_base64}`,
      x: 8.0,
      y: 0.3,
      w: 1.5,
      h: 0.6,
    });
  }
}

function renderKPISlide(
  pptx: PptxGenJS,
  block: KPIBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  // KPI Cards
  const cols = block.columns || 3;
  const cardWidth = 8.5 / cols;
  const startY = 1.2;

  block.kpis.forEach((kpi, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = 0.5 + col * (cardWidth + 0.2);
    const y = startY + row * 2.0;

    // Value (large number)
    slide.addText(kpi.value, {
      x,
      y,
      w: cardWidth,
      h: 1.0,
      fontSize: 48,
      fontFace: design.fonts.data,
      color: design.colors.primary.replace("#", ""),
      bold: true,
      align: "center",
    });

    // Unit
    if (kpi.unit) {
      slide.addText(kpi.unit, {
        x,
        y: y + 0.9,
        w: cardWidth,
        h: 0.4,
        fontSize: 14,
        fontFace: design.fonts.body,
        color: design.colors.neutral.replace("#", ""),
        align: "center",
      });
    }

    // Label
    slide.addText(kpi.label, {
      x,
      y: y + 1.3,
      w: cardWidth,
      h: 0.4,
      fontSize: 14,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      align: "center",
    });
  });
}

function renderTableSlide(
  pptx: PptxGenJS,
  block: TableBlock,
  design: ResolvedDesignSystem
): void {
  // 오버플로우 처리: 슬라이드당 최대 행 수 (기본값: 15)
  const maxRowsPerSlide = block.max_rows_per_slide || 15;
  const totalRows = block.rows.length;
  const slideCount = Math.ceil(totalRows / maxRowsPerSlide);

  // 각 슬라이드에 대해 테이블 렌더링
  for (let slideIdx = 0; slideIdx < slideCount; slideIdx++) {
    const slide = pptx.addSlide();
    const isLastSlide = slideIdx === slideCount - 1;

    // Title (with page indicator if multiple slides)
    const titleSuffix = slideCount > 1 ? ` (${slideIdx + 1}/${slideCount})` : "";
    slide.addText(block.title + titleSuffix, {
      x: 0.5,
      y: 0.3,
      w: 9.0,
      h: 0.6,
      fontSize: design.sizes.section_title,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });

    // Build table data
    const tableRows: PptxGenJS.TableRow[] = [];

    // Header row (on every slide)
    if (block.show_header !== false) {
      const headerRow: PptxGenJS.TableCell[] = block.columns.map((col) => ({
        text: col.header,
        options: {
          fill: { color: design.colors.header_bg.replace("#", "") },
          color: design.colors.header_text.replace("#", ""),
          bold: true,
          fontSize: design.sizes.table_header,
          fontFace: design.fonts.heading,
          align: col.align || "right",
          valign: "middle",
        },
      }));
      tableRows.push(headerRow);
    }

    // Data rows for this slide
    const startRow = slideIdx * maxRowsPerSlide;
    const endRow = Math.min(startRow + maxRowsPerSlide, totalRows);
    const rowsForSlide = block.rows.slice(startRow, endRow);

    rowsForSlide.forEach((row, localRowIndex) => {
      const globalRowIndex = startRow + localRowIndex;
      const dataRow: PptxGenJS.TableCell[] = block.columns.map((col) => {
        const value = row[col.key];
        const displayValue =
          value !== null && value !== undefined ? String(value) : "";

        const cellOptions: PptxGenJS.TextPropsOptions = {
          fontSize: design.sizes.table_body,
          fontFace: design.fonts.data,
          color: design.colors.neutral.replace("#", ""),
          align: col.align || "right",
          valign: "middle",
        };

        // Zebra stripe (based on global row index)
        if (block.zebra_stripe && globalRowIndex % 2 === 1) {
          cellOptions.fill = { color: design.colors.alt_row.replace("#", "") };
        }

        return { text: displayValue, options: cellOptions };
      });
      tableRows.push(dataRow);
    });

    // Footer rows (only on last slide)
    if (isLastSlide && block.footer_rows && block.footer_rows.length > 0) {
      block.footer_rows.forEach((row) => {
        const footerRow: PptxGenJS.TableCell[] = block.columns.map((col) => {
          const value = row[col.key];
          const displayValue =
            value !== null && value !== undefined ? String(value) : "";

          return {
            text: displayValue,
            options: {
              fontSize: design.sizes.table_body,
              fontFace: design.fonts.heading,
              color: design.colors.primary.replace("#", ""),
              bold: true,
              align: col.align || "right",
              valign: "middle",
              fill: { color: "E0E0E0" },
            },
          };
        });
        tableRows.push(footerRow);
      });
    }

    // Calculate column widths
    const colWidths = block.columns.map((col) => col.width || 1.5);

    // Add table
    const pos = block.position || { x: 0.5, y: 1.0 };
    slide.addTable(tableRows, {
      x: pos.x,
      y: pos.y,
      w: block.size?.w || 9.0,
      colW: colWidths,
      border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    });

    // Continuation indicator (not on last slide)
    if (!isLastSlide) {
      slide.addText("(continued on next slide...)", {
        x: 0.5,
        y: 5.0,
        w: 9.0,
        h: 0.3,
        fontSize: 9,
        fontFace: design.fonts.body,
        color: "999999",
        italic: true,
        align: "right",
      });
    }
  }
}

function renderChartSlide(
  pptx: PptxGenJS,
  block: ChartBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  const pos = block.position || { x: 0.5, y: 1.2 };
  const size = block.size || { w: 9.0, h: 4.0 };

  // If image_base64 is provided (pre-rendered from Plotly), use it
  if (block.image_base64) {
    slide.addImage({
      data: `data:image/png;base64,${block.image_base64}`,
      x: pos.x,
      y: pos.y,
      w: size.w,
      h: size.h,
    });
    return;
  }

  // Otherwise, render chart using PptxGenJS native chart
  if (!block.data) {
    slide.addText("(No chart data provided)", {
      x: pos.x,
      y: pos.y + size.h / 2,
      w: size.w,
      h: 0.5,
      fontSize: 14,
      color: "999999",
      align: "center",
    });
    return;
  }

  // Convert values to numbers
  const numericValues = block.data.values.map((v) => {
    if (v === null || v === undefined) return 0;
    return typeof v === "number" ? v : parseFloat(String(v)) || 0;
  });

  // Chart type mapping
  switch (block.chart_type) {
    case "bar":
      slide.addChart(pptx.ChartType.bar, [
        {
          name: block.data.series_name || "Values",
          labels: block.data.categories,
          values: numericValues,
        },
      ], {
        x: pos.x,
        y: pos.y,
        w: size.w,
        h: size.h,
        showTitle: false,
        barDir: "bar",
        chartColors: [design.colors.primary.replace("#", "")],
      });
      break;

    case "line":
      slide.addChart(pptx.ChartType.line, [
        {
          name: block.data.series_name || "Values",
          labels: block.data.categories,
          values: numericValues,
        },
      ], {
        x: pos.x,
        y: pos.y,
        w: size.w,
        h: size.h,
        showTitle: false,
        chartColors: [design.colors.primary.replace("#", "")],
        lineDataSymbol: "circle",
        lineSize: 2,
      });
      break;

    case "pie":
      slide.addChart(pptx.ChartType.pie, [
        {
          name: block.data.series_name || "Values",
          labels: block.data.categories,
          values: numericValues,
        },
      ], {
        x: pos.x,
        y: pos.y,
        w: size.w,
        h: size.h,
        showTitle: false,
        showPercent: true,
      });
      break;

    case "waterfall":
    default:
      // PptxGenJS doesn't have native waterfall, use pre-rendered image
      // or fallback to bar chart representation
      slide.addText(
        "(Waterfall chart requires pre-rendered image via image_base64)",
        {
          x: pos.x,
          y: pos.y + size.h / 2,
          w: size.w,
          h: 0.5,
          fontSize: 12,
          color: "999999",
          align: "center",
        }
      );
      break;
  }
}

function renderTextSlide(
  pptx: PptxGenJS,
  block: TextBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  let yPos = 0.3;

  // Title
  if (block.title) {
    slide.addText(block.title, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.6,
      fontSize: design.sizes.section_title,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.8;
  }

  // Risk level indicator
  if (block.risk_level) {
    const riskColors: Record<string, string> = {
      high: design.colors.negative,
      medium: "#F9A825",
      low: design.colors.positive,
    };
    const riskLabels: Record<string, string> = {
      high: "HIGH RISK",
      medium: "MEDIUM RISK",
      low: "LOW RISK",
    };

    slide.addText(riskLabels[block.risk_level] || "", {
      x: 0.5,
      y: yPos,
      w: 2.0,
      h: 0.4,
      fontSize: 12,
      fontFace: design.fonts.heading,
      color: "FFFFFF",
      bold: true,
      fill: { color: riskColors[block.risk_level]?.replace("#", "") || "666666" },
      align: "center",
    });
    yPos += 0.6;
  }

  // Content
  if (block.content) {
    slide.addText(block.content, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 2.0,
      fontSize: design.sizes.body,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      valign: "top",
    });
    yPos += 2.2;
  }

  // Bullet points
  if (block.bullet_points && block.bullet_points.length > 0) {
    const bulletText = block.bullet_points.map((point) => ({
      text: point,
      options: { bullet: true, indentLevel: 0 },
    }));

    slide.addText(bulletText, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 2.5,
      fontSize: design.sizes.body,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      valign: "top",
    });
  }
}

function renderClaimSlide(
  pptx: PptxGenJS,
  block: ClaimBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  let yPos = 0.3;

  // Category label (if present)
  if (block.category) {
    slide.addText(block.category.toUpperCase(), {
      x: 0.5,
      y: yPos,
      w: 2.0,
      h: 0.4,
      fontSize: 12,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.5;
  }

  // Verification status
  const statusColor = block.verified ? design.colors.positive : design.colors.negative;
  const statusText = block.verified ? "✓ VERIFIED" : "⚠ UNVERIFIED";

  slide.addText(statusText, {
    x: 7.0,
    y: 0.3,
    w: 2.5,
    h: 0.4,
    fontSize: 12,
    fontFace: design.fonts.heading,
    color: statusColor.replace("#", ""),
    bold: true,
    align: "right",
  });

  // Risk level indicator
  if (block.risk_level) {
    const riskColors: Record<string, string> = {
      high: design.colors.negative,
      medium: "#F9A825",
      low: design.colors.positive,
    };

    slide.addShape(pptx.ShapeType.rect, {
      x: 0.5,
      y: yPos,
      w: 0.1,
      h: 1.5,
      fill: { color: riskColors[block.risk_level]?.replace("#", "") || "666666" },
    });
  }

  // Claim text
  slide.addText(block.claim_text, {
    x: block.risk_level ? 0.8 : 0.5,
    y: yPos,
    w: 8.5,
    h: 1.5,
    fontSize: design.sizes.body,
    fontFace: design.fonts.body,
    color: design.colors.neutral.replace("#", ""),
    valign: "top",
  });
  yPos += 1.8;

  // Evidence references
  if (block.evidence_refs && block.evidence_refs.length > 0) {
    slide.addText("Evidence References:", {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.4,
      fontSize: 12,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.5;

    const evidenceText = block.evidence_refs.map((ref) => ({
      text: `• ${ref.source_type}: ${ref.source_id}${ref.description ? ` - ${ref.description}` : ""}`,
      options: { bullet: false, indentLevel: 0 },
    }));

    slide.addText(evidenceText, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 2.0,
      fontSize: 11,
      fontFace: design.fonts.data,
      color: design.colors.neutral.replace("#", ""),
      valign: "top",
    });
  }
}

function renderIssueSlide(
  pptx: PptxGenJS,
  block: IssueBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  // Filter issues if needed
  const issuesToShow = block.show_resolved
    ? block.issues
    : block.issues.filter((i) => i.status !== "resolved");

  if (issuesToShow.length === 0) {
    slide.addText("No issues to display.", {
      x: 0.5,
      y: 2.5,
      w: 9.0,
      h: 0.5,
      fontSize: design.sizes.body,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      align: "center",
    });
    return;
  }

  // Build issue table
  const severityColors: Record<string, string> = {
    critical: design.colors.negative.replace("#", ""),
    high: "E65100",
    medium: "F9A825",
    low: design.colors.positive.replace("#", ""),
  };

  const tableRows: PptxGenJS.TableRow[] = [
    // Header
    [
      { text: "ID", options: { fill: { color: design.colors.header_bg.replace("#", "") }, color: design.colors.header_text.replace("#", ""), bold: true, fontSize: 10, fontFace: design.fonts.heading } },
      { text: "Category", options: { fill: { color: design.colors.header_bg.replace("#", "") }, color: design.colors.header_text.replace("#", ""), bold: true, fontSize: 10, fontFace: design.fonts.heading } },
      { text: "Severity", options: { fill: { color: design.colors.header_bg.replace("#", "") }, color: design.colors.header_text.replace("#", ""), bold: true, fontSize: 10, fontFace: design.fonts.heading } },
      { text: "Issue", options: { fill: { color: design.colors.header_bg.replace("#", "") }, color: design.colors.header_text.replace("#", ""), bold: true, fontSize: 10, fontFace: design.fonts.heading } },
      { text: "Status", options: { fill: { color: design.colors.header_bg.replace("#", "") }, color: design.colors.header_text.replace("#", ""), bold: true, fontSize: 10, fontFace: design.fonts.heading } },
    ],
  ];

  issuesToShow.forEach((issue, idx) => {
    const rowFill = idx % 2 === 1 ? { color: design.colors.alt_row.replace("#", "") } : undefined;
    tableRows.push([
      { text: issue.issue_id, options: { fontSize: 9, fontFace: design.fonts.data, fill: rowFill } },
      { text: issue.category, options: { fontSize: 9, fontFace: design.fonts.data, fill: rowFill } },
      { text: issue.severity.toUpperCase(), options: { fontSize: 9, fontFace: design.fonts.heading, bold: true, color: severityColors[issue.severity] || "666666", fill: rowFill } },
      { text: issue.title, options: { fontSize: 9, fontFace: design.fonts.data, fill: rowFill } },
      { text: issue.status, options: { fontSize: 9, fontFace: design.fonts.data, fill: rowFill } },
    ]);
  });

  slide.addTable(tableRows, {
    x: 0.5,
    y: 1.0,
    w: 9.0,
    colW: [0.8, 1.2, 0.8, 4.7, 0.8],
    border: { type: "solid", pt: 0.5, color: "CCCCCC" },
  });
}

function renderMethodologySlide(
  pptx: PptxGenJS,
  block: MethodologyBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  let yPos = 1.0;

  // Introduction
  if (block.introduction) {
    slide.addText(block.introduction, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.8,
      fontSize: design.sizes.body,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      valign: "top",
    });
    yPos += 1.0;
  }

  // Steps
  block.steps.forEach((step) => {
    slide.addText(`${step.step}. ${step.title}`, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.4,
      fontSize: 13,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.4;

    if (step.description) {
      slide.addText(step.description, {
        x: 0.7,
        y: yPos,
        w: 8.8,
        h: 0.5,
        fontSize: 11,
        fontFace: design.fonts.body,
        color: design.colors.neutral.replace("#", ""),
        valign: "top",
      });
      yPos += 0.6;
    }
  });

  // Limitations
  if (block.limitations && block.limitations.length > 0) {
    yPos += 0.3;
    slide.addText("Limitations:", {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.4,
      fontSize: 12,
      fontFace: design.fonts.heading,
      color: design.colors.neutral.replace("#", ""),
      bold: true,
    });
    yPos += 0.4;

    const limitText = block.limitations.map((lim) => ({
      text: lim,
      options: { bullet: true, indentLevel: 0 },
    }));

    slide.addText(limitText, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 1.5,
      fontSize: 10,
      fontFace: design.fonts.body,
      color: design.colors.neutral.replace("#", ""),
      valign: "top",
    });
  }
}

function renderScopeSlide(
  pptx: PptxGenJS,
  block: ScopeBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  let yPos = 1.0;

  // Scope items as two-column table
  if (block.scope_items && block.scope_items.length > 0) {
    const scopeRows: PptxGenJS.TableRow[] = block.scope_items.map((item) => [
      { text: item.label, options: { fontSize: 11, fontFace: design.fonts.heading, bold: true, color: design.colors.primary.replace("#", "") } },
      { text: item.value, options: { fontSize: 11, fontFace: design.fonts.data, color: design.colors.neutral.replace("#", "") } },
    ]);

    slide.addTable(scopeRows, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      colW: [2.5, 6.5],
      border: { type: "solid", pt: 0.5, color: "CCCCCC" },
    });

    yPos += block.scope_items.length * 0.4 + 0.5;
  }

  // Definitions
  if (block.definitions && Object.keys(block.definitions).length > 0) {
    slide.addText("Definitions:", {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.4,
      fontSize: 12,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.5;

    const defRows: PptxGenJS.TableRow[] = Object.entries(block.definitions).map(([term, def]) => [
      { text: term, options: { fontSize: 10, fontFace: design.fonts.heading, bold: true, color: design.colors.neutral.replace("#", "") } },
      { text: def, options: { fontSize: 10, fontFace: design.fonts.body, color: design.colors.neutral.replace("#", "") } },
    ]);

    slide.addTable(defRows, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      colW: [2.0, 7.0],
      border: { type: "solid", pt: 0.5, color: "EEEEEE" },
    });
  }
}

function renderAppendixSlide(
  pptx: PptxGenJS,
  block: AppendixBlock,
  design: ResolvedDesignSystem
): void {
  const slide = pptx.addSlide();

  // Title
  slide.addText(block.title, {
    x: 0.5,
    y: 0.3,
    w: 9.0,
    h: 0.6,
    fontSize: design.sizes.section_title,
    fontFace: design.fonts.heading,
    color: design.colors.primary.replace("#", ""),
    bold: true,
  });

  let yPos = 1.0;

  // List of appendix items
  block.items.forEach((item, idx) => {
    slide.addText(`${idx + 1}. ${item.title}`, {
      x: 0.5,
      y: yPos,
      w: 9.0,
      h: 0.4,
      fontSize: 13,
      fontFace: design.fonts.heading,
      color: design.colors.primary.replace("#", ""),
      bold: true,
    });
    yPos += 0.4;

    if (item.content) {
      slide.addText(item.content, {
        x: 0.7,
        y: yPos,
        w: 8.8,
        h: 0.6,
        fontSize: 11,
        fontFace: design.fonts.body,
        color: design.colors.neutral.replace("#", ""),
        valign: "top",
      });
      yPos += 0.7;
    }

    if (item.reference_page) {
      slide.addText(`See page ${item.reference_page}`, {
        x: 0.7,
        y: yPos - 0.3,
        w: 8.8,
        h: 0.3,
        fontSize: 9,
        fontFace: design.fonts.body,
        color: design.colors.secondary.replace("#", ""),
        italic: true,
      });
    }

    yPos += 0.3;
  });
}

// =============================================================================
// Main Render Function
// =============================================================================

async function renderReport(schema: ReportSchema): Promise<Buffer> {
  const pptx = new PptxGenJS();

  // Merge design system with defaults (defaults ensure all required fields exist)
  const design: ResolvedDesignSystem = {
    colors: { ...DEFAULT_DESIGN.colors, ...schema.design_system?.colors } as DesignSystemColors,
    fonts: { ...DEFAULT_DESIGN.fonts, ...schema.design_system?.fonts } as DesignSystemFonts,
    sizes: { ...DEFAULT_DESIGN.sizes, ...schema.design_system?.sizes } as DesignSystemSizes,
  };

  // Set presentation properties
  pptx.layout = "LAYOUT_16x9";
  pptx.author = schema.meta.deal_name || "Auto FDD";
  pptx.title = `FDD Report - ${schema.meta.deal_name || "Untitled"}`;
  pptx.subject = "Financial Due Diligence Report";

  // Render each section
  for (const section of schema.sections) {
    switch (section.type) {
      case "cover":
        renderCoverSlide(pptx, section, design);
        break;
      case "kpi":
        renderKPISlide(pptx, section, design);
        break;
      case "table":
        renderTableSlide(pptx, section, design);
        break;
      case "chart":
        renderChartSlide(pptx, section, design);
        break;
      case "text":
        renderTextSlide(pptx, section, design);
        break;
      case "claim":
        renderClaimSlide(pptx, section, design);
        break;
      case "issue":
        renderIssueSlide(pptx, section, design);
        break;
      case "methodology":
        renderMethodologySlide(pptx, section, design);
        break;
      case "scope":
        renderScopeSlide(pptx, section, design);
        break;
      case "appendix":
        renderAppendixSlide(pptx, section, design);
        break;
      default:
        console.warn(`Unknown section type: ${(section as ReportBlock).type}`);
    }
  }

  // Write to buffer
  const data = await pptx.write({ outputType: "nodebuffer" });
  return data as Buffer;
}

// =============================================================================
// Routes
// =============================================================================

app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "pptx-service", version: "0.2.0" });
});

app.post("/render", async (req: Request, res: Response) => {
  try {
    const reportSchema = req.body as ReportSchema;

    // Validation
    if (!reportSchema || !reportSchema.meta) {
      res.status(400).json({ error: "Invalid report schema: missing meta" });
      return;
    }

    if (!reportSchema.sections || !Array.isArray(reportSchema.sections)) {
      res.status(400).json({ error: "Invalid report schema: missing sections array" });
      return;
    }

    // Render PPTX
    const buffer = await renderReport(reportSchema);

    // Return as file download
    const filename = `FDD_Report_${reportSchema.meta.deal_name || "Report"}_${Date.now()}.pptx`;

    res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
    res.setHeader("Content-Disposition", `attachment; filename="${encodeURIComponent(filename)}"`);
    res.setHeader("Content-Length", buffer.length);

    res.send(buffer);
  } catch (error) {
    console.error("Render error:", error);
    res.status(500).json({
      error: "Failed to render PPTX",
      message: error instanceof Error ? error.message : String(error),
    });
  }
});

// Preview endpoint - returns JSON summary instead of file
app.post("/preview", async (req: Request, res: Response) => {
  const reportSchema = req.body as ReportSchema;

  if (!reportSchema || !reportSchema.meta) {
    res.status(400).json({ error: "Invalid report schema: missing meta" });
    return;
  }

  res.json({
    deal_name: reportSchema.meta.deal_name,
    sections_count: reportSchema.sections?.length || 0,
    sections: reportSchema.sections?.map((s) => ({
      type: s.type,
      title: "title" in s ? s.title : undefined,
    })) || [],
  });
});

app.listen(PORT, () => {
  console.log(`pptx-service listening on port ${PORT}`);
});
