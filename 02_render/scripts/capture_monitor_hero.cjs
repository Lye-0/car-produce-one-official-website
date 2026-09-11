// Requires Playwright. PLAYWRIGHT_MODULE may point to an existing installation.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../..');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
    await page.goto(process.argv[2] || 'http://127.0.0.1:5173/');
    await page.waitForSelector('main .main-hero', { state: 'attached' });
    const hero = await page.locator('main .main-hero').evaluate(node => {
      const clone = node.cloneNode(true);
      clone.querySelector('.desktop-hero-background')?.remove();
      clone.classList.remove('desktop-live-hero');
      clone.removeAttribute('style');
      const link = clone.querySelector('.desktop-hero-link');
      if (link) {
        link.innerHTML = link.querySelector('.text-link').innerHTML;
        link.className = 'text-link';
      }
      return clone.outerHTML;
    });
    const css = fs.readFileSync(path.join(root, '01_website/src/globals.css'), 'utf8');
    const style = 'width:1280px;height:720px;--screen-font:64px;--screen-top:120px;--screen-side:102.4px;--screen-bottom:60px;--screen-heading-bottom:32px;--screen-letter-spacing:.12em;--screen-label:9px;--screen-copy:13px;--screen-footer-display:flex;--screen-link-margin:0px;--screen-giant:371.2px';
    await page.setContent('<style>' + css + '</style><div class="projected-screen" style="' + style + '">' + hero + '</div>');
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: process.argv[3] || path.join(root, '02_render/assets/monitor-hero.png') });
  } finally { await browser.close(); }
})();
