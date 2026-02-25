/**
 * E2E Auth Pages — 인증이 필요한 페이지 확인 (로그인 후 캡처)
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE = "http://localhost:3000";
const DIR = "./screenshots/auth-pages";

const PAGES = [
  { name: "01_dashboard", url: "/" },
  { name: "02_ma_transactions", url: "/ma/transactions" },
  { name: "03_im_documents", url: "/im" },
  { name: "04_analytics", url: "/analytics" },
  { name: "05_calendar", url: "/calendar" },
  { name: "06_admin_users", url: "/admin/users" },
  { name: "07_admin_activity", url: "/admin/activity" },
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

  // Step 1: Go to login page
  console.log("Logging in...");
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle", timeout: 15000 });

  // Step 2: Fill login form and submit
  // AUTH_ENABLED=false means /auth/me returns dev user without actual login
  // But the SPA checks isAuthenticated on mount. Let's try navigating to a working page first.
  // Actually: go to /fdd/deals first (we know this works) to establish auth
  await page.goto(`${BASE}/fdd/deals`, { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(2000);

  // Check if we're authenticated by looking for sidebar items
  const sidebarText = await page.textContent("nav");
  const isAuth = sidebarText && sidebarText.includes("Home");
  console.log(`Auth state: ${isAuth ? "authenticated" : "not authenticated"}`);

  if (!isAuth) {
    console.log("Not authenticated. Trying login form...");
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', "system@autofdd.dev");
    await page.fill('input[type="password"]', "any-password");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
  }

  console.log("\n=== Auth-Required Pages ===\n");

  for (const { name, url } of PAGES) {
    try {
      await page.goto(`${BASE}${url}`, { waitUntil: "networkidle", timeout: 15000 });
      await page.waitForTimeout(1000);

      const finalUrl = page.url();
      const onLogin = finalUrl.includes("/login");
      await page.screenshot({ path: `${DIR}/${name}.png` });
      console.log(`${onLogin ? "✗" : "✓"} ${name.padEnd(25)} ${onLogin ? "→ LOGIN" : "OK"}`);
    } catch (err) {
      console.log(`✗ ${name.padEnd(25)} ${err.message.slice(0, 60)}`);
      try { await page.screenshot({ path: `${DIR}/${name}_error.png` }); } catch {}
    }
  }

  console.log(`\nConsole errors: ${errors.length}`);
  for (const e of errors.slice(0, 10)) {
    console.log(`  [${new URL(e.url).pathname}] ${e.text.slice(0, 100)}`);
  }

  await browser.close();
}

run().catch(console.error);
