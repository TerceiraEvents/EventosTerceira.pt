import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');

// Fixtures mirror the EN/PT Source and Instagram variants of the card include.
function actionRow(mapLabel, sourceHtml, flagLabel) {
  return '<div class="event-card-actions">'
    + `<a class="event-map-link" data-safe-link href="https://www.example.test/maps" target="_blank" rel="noopener noreferrer">📍 ${mapLabel}</a>`
    + (sourceHtml
      ? `<a class="event-source" data-safe-link href="https://www.example.test/source" target="_blank" rel="noopener noreferrer">${sourceHtml}</a>`
      : '')
    + `<button type="button" class="event-flag-btn">🚩 ${flagLabel}</button>`
    + '</div>';
}

const MEASURE_SCRIPT = `<script>(function () {
  function rect(el) {
    var box = el.getBoundingClientRect();
    return { top: box.top, left: box.left, right: box.right, bottom: box.bottom,
      width: box.width, height: box.height };
  }
  var rows = Array.prototype.map.call(
    document.querySelectorAll('.event-card-actions'),
    function (row) {
      return Array.prototype.map.call(row.querySelectorAll('a, button'), rect);
    });
  var payload = JSON.stringify({
    viewportWidth: innerWidth,
    availableWidth: document.documentElement.clientWidth,
    docWidth: document.documentElement.scrollWidth,
    rows: rows,
  });
  var target = parent.document.getElementById('geometry-result');
  target.textContent = payload;
})();</script>`;

function fixtureHtml(css, width) {
  const content = '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width, initial-scale=1">'
    + `<title>card action geometry</title><style>${css}</style></head><body>`
    + '<article class="special-event event-summary"><div class="event-details">'
    + '<h3 class="event-name">Evening concert</h3>'
    + `${actionRow('Open in Maps', '📸 View on Instagram', 'Suggest an edit')}`
    + '</div></article>'
    + '<article class="special-event event-summary"><div class="event-details">'
    + '<h3 class="event-name">Noite de fados</h3>'
    + `${actionRow('Abrir no Maps', '📸 Ver no Instagram', 'Sugerir uma alteração')}`
    + '</div></article>'
    + '<article class="special-event event-summary"><div class="event-details">'
    + '<h3 class="event-name">Gallery opening</h3>'
    + `${actionRow('Open in Maps', 'Source', 'Suggest an edit')}`
    + '</div></article>'
    + '<article class="special-event event-summary"><div class="event-details">'
    + '<h3 class="event-name">Exposição</h3>'
    + `${actionRow('Abrir no Maps', 'Fonte', 'Sugerir uma alteração')}`
    + '</div></article>'
    + `${MEASURE_SCRIPT}</body></html>`;
  const srcdoc = content.replaceAll('&', '&amp;').replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  return '<!doctype html><html><body><div id="geometry-result" hidden></div>'
    + `<iframe title="Card fixtures" style="width:${width}px;height:2400px;border:0" srcdoc="${srcdoc}"></iframe>`
    + '</body></html>';
}

function resolveChrome() {
  if (process.env.CHROME_BIN) return process.env.CHROME_BIN;
  for (const candidate of ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium']) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error('no headless Chrome/Chromium binary found (tried CHROME_BIN and well-known '
    + 'paths); GitHub-hosted ubuntu runners provide google-chrome');
}

function renderWidth(binary, pageUrl, width, timeoutMs) {
  return new Promise((resolveRender, rejectRender) => {
    const fixtureDir = dirname(fileURLToPath(pageUrl));
    execFile(binary, ['--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
      `--user-data-dir=${join(fixtureDir, 'profile-' + width)}`, '--window-size=1280,800', '--dump-dom', pageUrl],
    { timeout: timeoutMs, maxBuffer: 16 * 1024 * 1024,
      env: { ...process.env, XDG_CACHE_HOME: join(fixtureDir, 'cache'), XDG_CONFIG_HOME: join(fixtureDir, 'config') } },
    (error, stdout, stderr) => {
      if (error) {
        rejectRender(new Error(`headless chrome failed at ${width}px (${error.signal || error.code}): ${stderr.slice(-1000)}`));
        return;
      }
      const match = /<div id="geometry-result"[^>]*>(.*?)<\/div>/s.exec(stdout);
      if (!match) { rejectRender(new Error(`no rendered measurements in dumped DOM at ${width}px`)); return; }
      try {
        resolveRender(JSON.parse(match[1]));
      } catch (parseError) {
        rejectRender(new Error(`unparsable measurements at ${width}px: ${parseError.message}`));
      }
    });
  });
}

function flexLines(actions) {
  const lines = [];
  for (const action of actions) {
    const line = lines.find((candidate) => candidate.some((other) => {
      const overlap = Math.min(other.bottom, action.bottom) - Math.max(other.top, action.top);
      return overlap > Math.min(other.height, action.height) / 2;
    }));
    if (line) line.push(action);
    else lines.push([action]);
  }
  return lines;
}

test('card action rows align and wrap within real 1280px and 320px frame viewports', async (t) => {
  const timeoutMs = Number(process.env.CARD_GEOMETRY_TIMEOUT_MS || 60000);
  const css = readFileSync(join(repoRoot, 'assets', 'css', 'style.css'), 'utf8');
  const fixtureDir = mkdtempSync(join(tmpdir(), 'card-geometry-page-'));
  t.after(() => rmSync(fixtureDir, { recursive: true, force: true }));
  const binary = resolveChrome();

  for (const width of [1280, 320]) {
    const page = join(fixtureDir, `actions-${width}.html`);
    writeFileSync(page, fixtureHtml(css, width));
    const pageUrl = `file://${encodeURI(page)}`;
    const measured = await renderWidth(binary, pageUrl, width, timeoutMs);
    assert.equal(measured.viewportWidth, width, 'the frame uses the requested CSS viewport width');
    assert.equal(measured.rows.length, 4, `expected four action rows at ${width}px`);
    for (const [index, actions] of measured.rows.entries()) {
      assert.equal(actions.length, 3, `row ${index} keeps all three actions at ${width}px`);
      const lines = flexLines(actions);
      if (width === 1280) {
        assert.equal(lines.length, 1,
          `row ${index} stays on one line at desktop width (tops ${actions.map((a) => a.top.toFixed(1)).join(', ')})`);
      }
      if (width === 320) assert.ok(lines.length > 1, `row ${index} exercises wrapping at 320px`);
      for (const [lineIndex, line] of lines.entries()) {
        const centers = line.map((action) => action.top + action.height / 2);
        assert.ok(Math.max(...centers) - Math.min(...centers) <= 1,
          `row ${index} line ${lineIndex} controls align at ${width}px (centers ${centers.map((v) => v.toFixed(1)).join(', ')})`);
        for (const [position, action] of line.entries()) {
          assert.ok(action.width >= 44 && action.height >= 44,
            `row ${index} line ${lineIndex} action ${position} target is at least 44x44px at ${width}px`
            + ` (got ${action.width.toFixed(1)}x${action.height.toFixed(1)})`);
          assert.ok(action.left >= -1 && action.right <= measured.availableWidth + 1,
            `row ${index} line ${lineIndex} action ${position} stays in bounds at ${width}px`
            + ` (left ${action.left.toFixed(1)}, right ${action.right.toFixed(1)})`);
        }
      }
    }
    assert.ok(measured.docWidth <= measured.availableWidth + 1,
      `long EN/PT labels wrap without horizontal overflow at ${width}px (document ${measured.docWidth})`);
  }
});
