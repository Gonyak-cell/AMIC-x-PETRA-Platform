import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const pages = [
  { file: '0_thumbnail.html', output: '0_thumbnail.png', width: 1280, height: 800 },
  { file: '1_gp_search.html', output: '1_gp_search.png', width: 1280, height: 900 },
  { file: '2_financial_info.html', output: '2_financial_info.png', width: 1280, height: 900 },
  { file: '3_disclosure_monitor.html', output: '3_disclosure_monitor.png', width: 1280, height: 900 },
  { file: '4_fund_info.html', output: '4_fund_info.png', width: 1280, height: 900 },
  { file: '5_im_report.html', output: '5_im_report.png', width: 1280, height: 900 },
];

const browser = await chromium.launch();

for (const p of pages) {
  const ctx = await browser.newContext({ viewport: { width: p.width, height: p.height } });
  const page = await ctx.newPage();
  const filePath = path.join(__dirname, p.file).replace(/\\/g, '/');
  await page.goto(`file:///${filePath}`);
  await page.waitForTimeout(500);
  const outputPath = path.join(__dirname, p.output);
  await page.screenshot({ path: outputPath, fullPage: false });
  console.log(`✓ ${p.output}`);
  await ctx.close();
}

await browser.close();
console.log('\nDone! All screenshots saved.');
