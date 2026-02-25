/**
 * E2E MA Workspace Tabs — 15탭 스크린샷
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE = "http://localhost:3000";
const DIR = "./screenshots/ma-tabs";

// Use the created transaction ID
const TXN_ID = "ac7fea30-8c31-4cdb-bf7d-226b87109311";

const TABS = [
  { name: "01_overview", path: "" },
  { name: "02_engagement", path: "/engagement" },
  { name: "03_team", path: "/team" },
  { name: "04_buyers", path: "/buyers" },
  { name: "05_ndas", path: "/ndas" },
  { name: "06_bids", path: "/bids" },
  { name: "07_dd_checklist", path: "/dd-checklist" },
  { name: "08_contracts", path: "/contracts" },
  { name: "09_closing", path: "/closing" },
  { name: "10_pmi", path: "/pmi" },
  { name: "11_earnout", path: "/earnout" },
  { name: "12_risks", path: "/risks" },
  { name: "13_compliance", path: "/compliance" },
  { name: "14_notes_approvals", path: "/notes-approvals" },
  { name: "15_timeline", path: "/timeline" },
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

  // First visit a page to establish auth
  await page.goto(`${BASE}/fdd/deals`, { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(2000);

  console.log("=== MA Workspace Tabs ===\n");

  for (const { name, path } of TABS) {
    const url = `${BASE}/ma/transactions/${TXN_ID}${path}`;
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
      await page.waitForTimeout(1000);

      const finalUrl = page.url();
      const redirected = finalUrl.includes("/login") ? " → LOGIN" : "";
      await page.screenshot({ path: `${DIR}/${name}.png` });
      console.log(`✓ ${name.padEnd(25)} ${redirected || "OK"}`);
    } catch (err) {
      console.log(`✗ ${name.padEnd(25)} ${err.message.slice(0, 60)}`);
      try { await page.screenshot({ path: `${DIR}/${name}_error.png` }); } catch {}
    }
  }

  // Also capture the transaction list page
  try {
    await page.goto(`${BASE}/ma/transactions`, { waitUntil: "networkidle", timeout: 15000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${DIR}/00_pipeline.png` });
    console.log(`✓ ${"00_pipeline".padEnd(25)} OK`);
  } catch {}

  console.log(`\nConsole errors: ${errors.length}`);
  for (const e of errors.slice(0, 10)) {
    console.log(`  [${new URL(e.url).pathname}] ${e.text.slice(0, 100)}`);
  }

  await browser.close();
}

run().catch(console.error);
