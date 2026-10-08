import { mkdtempSync, copyFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';

// Real installer subprocess, HTTP/WS relay process, decoder, and WebAudio.
// The only simulated services are the Kasm HTML shell and audio relay boundary.
const project = fileURLToPath(new URL('../../', import.meta.url));
let directory;
let browser;
const resources = [];

beforeAll(async () => {
  directory = mkdtempSync(join(tmpdir(), 'tor-audio-'));
  for (const name of ['index.html', 'vnc.html']) {
    copyFileSync(join(project, 'tests/fixtures/kasm-sidebar.html'), join(directory, name));
  }
  execFileSync('python3', [join(project, 'install.py'), directory]);
  browser = await chromium.launch({ headless: true });
});
afterEach(async () => {
  for (const cleanup of resources.splice(0).reverse()) await cleanup();
});
afterAll(async () => {
  await browser?.close();
  if (directory) rmSync(directory, { recursive: true, force: true });
});

async function open(mode = 'stream', entry = '/') {
  const child = spawn('node', [join(project, 'tests/helpers/relay-server.mjs'), directory, mode],
    { stdio: ['ignore', 'pipe', 'pipe'] });
  resources.push(() => new Promise(resolve => {
    if (child.exitCode !== null) return resolve();
    child.once('exit', resolve);
    child.kill();
  }));
  const url = await new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => reject(new Error('Relay startup timed out: ' + stderr)), 5000);
    child.stderr.on('data', chunk => { stderr += chunk; });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', code => { clearTimeout(timer); reject(new Error(`Relay exited ${code}: ${stderr}`)); });
    child.stdout.on('data', chunk => {
      stdout += chunk;
      if (stdout.includes('\n')) { clearTimeout(timer); resolve(JSON.parse(stdout.split('\n')[0]).url); }
    });
  });
  const page = await browser.newPage();
  resources.push(() => page.close());
  // Observe samples at the WebAudio output boundary without replacing playback.
  await page.addInitScript(() => {
    window.audioProbe = { contexts: [], buffers: 0, peak: 0 };
    const NativeContext = window.AudioContext;
    window.AudioContext = new Proxy(NativeContext, {
      construct(Target, args) {
        const context = new Target(...args);
        audioProbe.contexts.push(context);
        const create = context.createBufferSource.bind(context);
        context.createBufferSource = () => {
          const source = create();
          const start = source.start.bind(source);
          source.start = (...args) => {
            audioProbe.buffers++;
            for (const sample of source.buffer.getChannelData(0)) {
              audioProbe.peak = Math.max(audioProbe.peak, Math.abs(sample));
            }
            return start(...args);
          };
          return source;
        };
        return context;
      },
    });
  });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(url + entry);
  const button = page.locator('#homelab_audio_button');
  await button.waitFor();
  return { page, button, errors, stats: () => fetch(url + '/stats').then(r => r.json()) };
}

async function expectClosed(page) {
  await page.waitForFunction(() => audioProbe.contexts.every(context => context.state === 'closed'));
}

describe('installed Kasm audio sidebar', () => {
  it.each(['/', '/vnc.html'])('plays non-silent audio only after a click from %s', async entry => {
    const { page, button, stats, errors } = await open('stream', entry);
    expect((await stats()).connections).toBe(0);
    expect(await page.evaluate(() => audioProbe.contexts.length)).toBe(0);
    await button.click();
    await page.waitForFunction(() => audioProbe.buffers > 5 && audioProbe.peak > 0.05);
    expect(await button.getAttribute('aria-pressed')).toBe('true');
    expect(await page.evaluate(() => audioProbe.contexts[0].state)).toBe('running');
    await button.click();
    await expectClosed(page);
    await expect.poll(async () => (await stats()).active).toBe(0);
    expect(errors).toEqual([]);
  });

  it('reconnects repeatedly without leaking contexts or sockets', async () => {
    const { page, button, stats, errors } = await open();
    for (let attempt = 0; attempt < 3; attempt++) {
      await button.click();
      await expect.poll(() => button.getAttribute('aria-pressed')).toBe('true');
      await button.click();
      await expectClosed(page);
      await expect.poll(async () => (await stats()).active).toBe(0);
    }
    expect((await stats()).connections).toBe(3);
    expect(errors).toEqual([]);
  });

  it('closes playback on desktop disconnect', async () => {
    const { page, button, stats } = await open();
    await button.click();
    await page.waitForFunction(() => audioProbe.buffers > 0);
    await page.locator('#noVNC_disconnect_button').click();
    await expectClosed(page);
    expect(await button.isDisabled()).toBe(true);
    await expect.poll(async () => (await stats()).active).toBe(0);
  });

  it.each(['reject', 'close'])('reports a %s relay and releases playback resources', async mode => {
    const { page, button, errors } = await open(mode);
    await button.click();
    await expect.poll(() => page.locator('#homelab_audio_status').textContent()).toMatch(/failed|disconnected/);
    await expectClosed(page);
    expect(await button.isDisabled()).toBe(false);
    expect(await button.getAttribute('aria-pressed')).toBe('false');
    expect(errors).toEqual([]);
  });

  it('times out a stalled WebSocket handshake', async () => {
    const { page, button } = await open('hang');
    await page.clock.install();
    await button.click();
    await page.clock.fastForward(12001);
    await expect.poll(() => page.locator('#homelab_audio_status').textContent()).toMatch(/timed out/);
    await expectClosed(page);
    expect(await button.isDisabled()).toBe(false);
  });

  it('stops cleanly when the browser suspends audio', async () => {
    const { page, button, stats } = await open();
    await button.click();
    await page.waitForFunction(() => audioProbe.buffers > 0);
    await page.evaluate(() => audioProbe.contexts[0].suspend());
    await expect.poll(() => page.locator('#homelab_audio_status').textContent()).toMatch(/paused/);
    await expectClosed(page);
    await expect.poll(async () => (await stats()).active).toBe(0);
  });

  it('does not open a socket if the desktop disconnects while audio resume is pending', async () => {
    const { page, button, stats, errors } = await open();
    await page.evaluate(() => {
      AudioContext.prototype.resume = () => new Promise(resolve => { window.finishResume = resolve; });
    });
    await button.click();
    await page.locator('#noVNC_disconnect_button').click();
    await page.evaluate(() => finishResume());
    await expectClosed(page);
    expect((await stats()).connections).toBe(0);
    expect(await button.isDisabled()).toBe(true);
    expect(errors).toEqual([]);
  });
});
