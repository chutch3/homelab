import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { execFileSync } from 'node:child_process';

execFileSync('bundle', ['exec', 'ruby', 'script/export-javascript-tests.rb'], { stdio: 'inherit' });
const root = resolve('tmp/javascript-tests');
const sources = JSON.parse(await readFile(resolve(root, 'sources.json'), 'utf8'));
const server = createServer(async (request, response) => {
  try {
    const pathname = new URL(request.url, 'http://localhost').pathname;
    if (pathname === '/') {
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.end('<!doctype html><html><body><div id="jasmine_content"></div></body></html>');
      return;
    }
    const path = resolve(root, `.${pathname}`);
    if (!path.startsWith(root + sep)) throw new Error('Invalid asset path');
    response.setHeader('Content-Type', 'application/javascript; charset=utf-8');
    response.end(await readFile(path));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || undefined,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.addScriptTag({ path: 'node_modules/jasmine-core/lib/jasmine-core/jasmine.js' });
  await page.addScriptTag({ path: 'node_modules/jasmine-core/lib/jasmine-core/jasmine-html.js' });
  await page.addScriptTag({ path: 'node_modules/jasmine-core/lib/jasmine-core/boot0.js' });
  await page.evaluate(() => {
    window.testResults = { count: 0, failures: [], done: false };
    jasmine.getEnv().configure({ random: true });
    jasmine.getEnv().addReporter({
      specDone(result) {
        window.testResults.count++;
        if (result.status !== 'passed') window.testResults.failures.push(result);
      },
      jasmineDone(result) {
        window.testResults.overall = result;
        window.testResults.done = true;
      },
    });
  });
  for (const source of sources) await page.addScriptTag({ url: `/${source}` });
  await page.evaluate(() => new Promise(resolve => jQuery(resolve)));
  await page.evaluate(() => jasmine.getEnv().execute());
  await page.waitForFunction(() => window.testResults.done, null, { timeout: 120000 });
  const results = await page.evaluate(() => window.testResults);
  console.log(JSON.stringify(results, null, 2));
  if (!results.count || results.failures.length || results.overall.overallStatus !== 'passed' || errors.length) {
    console.error(errors);
    process.exitCode = 1;
  }
} finally {
  await browser.close();
  server.close();
}
