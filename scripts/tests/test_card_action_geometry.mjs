import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');

// Action-row markup mirrors _includes/special_event_card.html: a Maps link,
// a source link (Instagram and generic variants), and the Suggest-an-edit
// button, in both publish languages with the longest real labels.
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
    var style = getComputedStyle(el);
    return { top: box.top, left: box.left, right: box.right, bottom: box.bottom,
      width: box.width, height: box.height, marginTop: style.marginTop };
  }
  var rows = Array.prototype.map.call(
    document.querySelectorAll('.event-card-actions'),
    function (row) {
      return Array.prototype.map.call(row.querySelectorAll('a, button'), rect);
    });
  var payload = JSON.stringify({
    viewportWidth: document.documentElement.clientWidth,
    docWidth: document.documentElement.scrollWidth,
    rows: rows,
  });
  var target = document.getElementById('geometry-result');
  target.textContent = payload;
})();</script>`;

function fixtureHtml(css) {
  return '<!doctype html><html lang="en"><head><meta charset="utf-8">'
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
    + '<div id="geometry-result"></div>'
    + `${MEASURE_SCRIPT}</body></html>`;
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
    execFile(binary, ['--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
      `--window-size=${width},800`, '--dump-dom', pageUrl],
    { timeout: timeoutMs, maxBuffer: 16 * 1024 * 1024 },
    (error, stdout) => {
      if (error) { rejectRender(new Error(`headless chrome failed at ${width}px: ${error.message}`)); return; }
      const match = /<div id="geometry-result">(.*?)<\/div>/s.exec(stdout);
      if (!match) { rejectRender(new Error(`no rendered measurements in dumped DOM at ${width}px`)); return; }
      try {
        resolveRender(JSON.parse(match[1]));
      } catch (parseError) {
        rejectRender(new Error(`unparseable measurements at ${width}px: ${parseError.message}`));
      }
    });
  });
}

// Group actions by rendered flex line: actions whose tops agree within 1px
// share a line; wrapped lines each align independently.
function flexLines(actions) {
  const lines = [];
  for (const action of actions) {
    const line = lines.find((candidate) => Math.abs(candidate[0].top - action.top) <= 1);
    if (line) line.push(action);
    else lines.push([action]);
  }
  return lines;
}

test('card action rows align with uniform targets and wrap without overflow', async () => {
  const timeoutMs = Number(process.env.CARD_GEOMETRY_TIMEOUT_MS || 60000);
  const css = readFileSync(join(repoRoot, 'assets', 'css', 'style.css'), 'utf8');
  const page = join(mkdtempSync(join(tmpdir(), 'card-geometry-page-')), 'actions.html');
  writeFileSync(page, fixtureHtml(css));
  const pageUrl = `file://${encodeURI(page)}`;
  const binary = resolveChrome();

  for (const width of [1280, 320]) {
    const measured = await renderWidth(binary, pageUrl, width, timeoutMs);
    assert.equal(measured.rows.length, 4, `expected four action rows at ${width}px`);
    for (const [index, actions] of measured.rows.entries()) {
      assert.equal(actions.length, 3, `row ${index} keeps all three actions at ${width}px`);
      const margins = new Set(actions.map((action) => action.marginTop));
      assert.equal(margins.size, 1,
        `row ${index} actions use uniform spacing at ${width}px (margins ${[...margins].join(', ')})`);
      const lines = flexLines(actions);
      if (width === 1280) {
        assert.equal(lines.length, 1,
          `row ${index} stays on one line at desktop width (tops ${actions.map((a) => a.top.toFixed(1)).join(', ')})`);
      }
      for (const [lineIndex, line] of lines.entries()) {
        const tops = line.map((action) => action.top);
        assert.ok(Math.max(...tops) - Math.min(...tops) <= 1,
          `row ${index} line ${lineIndex} controls align at ${width}px (tops ${tops.map((v) => v.toFixed(1)).join(', ')})`);
        for (const [position, action] of line.entries()) {
          assert.ok(action.width >= 44 && action.height >= 44,
            `row ${index} line ${lineIndex} action ${position} target is at least 44x44px at ${width}px`
            + ` (got ${action.width.toFixed(1)}x${action.height.toFixed(1)})`);
          assert.ok(action.left >= -1 && action.right <= width + 1,
            `row ${index} line ${lineIndex} action ${position} stays in bounds at ${width}px`
            + ` (left ${action.left.toFixed(1)}, right ${action.right.toFixed(1)})`);
        }
      }
    }
    assert.ok(measured.docWidth <= width + 1,
      `long EN/PT labels wrap without horizontal overflow at ${width}px (document ${measured.docWidth})`);
  }
});
