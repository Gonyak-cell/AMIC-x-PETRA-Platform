/**
 * E2E Dashboard + Auth Pages — 간소화 버전
 * AUTH_ENABLED=false 상태에서 /auth/me가 dev user를 반환하므로
 * 로그인 없이 바로 페이지에 접근하여 캡처한다.
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE = "http://localhost:3000";
const DIR = "./screenshots/dashboard";

const PAGES = [
  { name: "01_dashboard", url: "/" },
  { name: "02_im_documents", url: "/im" },
  { name: "03_im_create", url: "/im/new" },
  { name: "04_analytics", url: "/analytics" },
  { name: "05_calendar", url: "/calendar" },
  { name: "06_kiis_dashboard", url: "/kiis" },
  { name: "07_kiis_gps", url: "/kiis/funds" },
  { name: "08_kiis_companies", url: "/kiis/companies" },
  { name: "09_fdd_deals", url: "/fdd/deals" },
  { name: "10_exports", url: "/exports" },
  { name: "11_settings", url: "/settings" },
  { name: "12_help", url: "/help" },
];

async function run() {
  mkdirSync(DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  const errors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push({ url: page.url(), text: msg.text() });
  });

  console.log("=== Dashboard & Core Pages ===\n");

  for (const { name, url } of PAGES) {
    try {
      await page.goto(`${BASE}${url}`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1500);

      const finalUrl = page.url();
      const onLogin = finalUrl.includes("/login");
      await page.screenshot({ path: `${DIR}/${name}.png` });
      console.log(`${onLogin ? "✗" : "✓"} ${name.padEnd(25)} ${onLogin ? "→ LOGIN" : "OK"}`);
    } catch (err) {
      console.log(`✗ ${name.padEnd(25)} ${err.message.slice(0, 80)}`);
      try { await page.screenshot({ path: `${DIR}/${name}_error.png` }); } catch {}
    }
  }

  console.log(`\nConsole errors: ${errors.length}`);
  for (const e of errors.slice(0, 15)) {
    console.log(`  [${new URL(e.url).pathname}] ${e.text.slice(0, 120)}`);
  }

  await browser.close();
}

run().catch(console.error);
