/**
 * E2E Visual Check — 핵심 페이지 스크린샷 캡처
 * Usage: node e2e-visual-check.mjs
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE = "http://localhost:3000";
const SCREENSHOT_DIR = "./screenshots";

const PAGES = [
  // 핵심 페이지
  { name: "01_login", url: "/login" },
  { name: "02_dashboard", url: "/" },
  { name: "03_ma_transactions", url: "/ma/transactions" },
  { name: "04_ma_create", url: "/ma/transactions/new" },
  { name: "05_kiis_gps", url: "/kiis/funds" },
  { name: "06_fdd_deals", url: "/fdd/deals" },
  { name: "07_im_documents", url: "/im" },
  { name: "08_kiis_dashboard", url: "/kiis" },
  { name: "09_kiis_companies", url: "/kiis/companies" },
  { name: "10_kiis_funds_all", url: "/kiis/funds/all" },
  { name: "11_im_create", url: "/im/new" },
  { name: "12_analytics", url: "/analytics" },
  { name: "13_calendar", url: "/calendar" },
  { name: "14_exports", url: "/exports" },
  { name: "15_help", url: "/help" },
  { name: "16_settings", url: "/settings/profile" },
];

// MA 워크스페이스 15탭 검증용 (txnId 동적 생성)
const MA_TABS = [
  "overview", "engagement", "team", "buyers", "timeline",
  "ndas", "bids", "dd-checklist", "contracts", "closing",
  "pmi", "earnout", "risks", "compliance", "notes-approvals",
];

async function run() {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  // 콘솔 에러 수집
  const errors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push({ url: page.url(), text: msg.text() });
    }
  });
  page.on("pageerror", (err) => {
    errors.push({ url: page.url(), text: err.message });
  });

  console.log("=== E2E Visual Check Start ===\n");

  // --- 핵심 페이지 스크린샷 ---
  for (const { name, url } of PAGES) {
    const fullUrl = `${BASE}${url}`;
    try {
      const response = await page.goto(fullUrl, {
        waitUntil: "networkidle",
        timeout: 15000,
      });
      await page.waitForTimeout(1000);

      const status = response?.status() ?? "N/A";
      const path = `${SCREENSHOT_DIR}/${name}.png`;
      await page.screenshot({ path, fullPage: false });

      const finalUrl = page.url();
      const redirected = finalUrl !== fullUrl ? ` → ${finalUrl}` : "";
      console.log(`✓ ${name.padEnd(30)} ${status}  ${url}${redirected}`);
    } catch (err) {
      console.log(`✗ ${name.padEnd(30)} ERROR  ${url}  ${err.message.slice(0, 80)}`);
      try {
        await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}_error.png` });
      } catch {}
    }
  }

  // --- MA 워크스페이스 15탭 검증 ---
  console.log("\n=== MA Workspace 15-Tab Check ===\n");

  // 기존 거래 목록에서 가져오기 (nginx: /api/ma/* → deal-mgmt /api/v1/*)
  let txnId = null;
  try {
    const res = await page.evaluate(async () => {
      const r = await fetch("/api/ma/transactions");
      if (!r.ok) return null;
      const data = await r.json();
      return data.items?.[0];
    });
    txnId = res?.id;
  } catch {}

  // 없으면 생성
  if (!txnId) {
    try {
      const res = await page.evaluate(async () => {
        const r = await fetch("/api/ma/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "E2E Test Deal",
            code_name: "EAGLE",
            side: "SELL",
            target_company_name: "Test Corp",
            client_name: "Test Client",
            lead_advisor_email: "test@test.com",
          }),
        });
        if (!r.ok) return null;
        return r.json();
      });
      txnId = res?.id;
    } catch {}
  }

  if (txnId) {
    console.log(`  Transaction ID: ${txnId}\n`);
    for (const tab of MA_TABS) {
      const tabUrl = `/ma/transactions/${txnId}/${tab}`;
      try {
        await page.goto(`${BASE}${tabUrl}`, { waitUntil: "networkidle", timeout: 15000 });
        await page.waitForTimeout(500);
        const name = `ma_tab_${tab}`;
        await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png`, fullPage: false });
        console.log(`  ✓ ${tab.padEnd(20)} OK`);
      } catch (err) {
        console.log(`  ✗ ${tab.padEnd(20)} ERROR  ${err.message.slice(0, 60)}`);
      }
    }
  } else {
    console.log("  ⚠ No transaction found — skipping tab check");
    // 빈 워크스페이스라도 렌더링 에러 없는지 확인
    try {
      await page.goto(`${BASE}/ma/transactions/00000000-0000-0000-0000-000000000000/overview`, {
        waitUntil: "networkidle",
        timeout: 15000,
      });
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/ma_tab_empty.png`, fullPage: false });
      console.log("  ✓ Empty workspace renders without crash");
    } catch (err) {
      console.log(`  ✗ Empty workspace  ${err.message.slice(0, 60)}`);
    }
  }

  console.log(`\n=== Console Errors (${errors.length}) ===`);
  for (const e of errors.slice(0, 20)) {
    console.log(`  [${new URL(e.url).pathname}] ${e.text.slice(0, 120)}`);
  }
  if (errors.length > 20) console.log(`  ... and ${errors.length - 20} more`);

  await browser.close();
  console.log(`\nScreenshots saved to ${SCREENSHOT_DIR}/`);
}

run().catch(console.error);
