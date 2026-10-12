import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { checkTokens, contrast } from '../check_discovery_tokens.js';
const manifest = JSON.parse(readFileSync(new URL('../../docs/discovery-tokens.json', import.meta.url), 'utf8'));
const css = readFileSync(new URL('../../assets/css/style.css', import.meta.url), 'utf8');

test('documented website color inventory matches the actual CSS and contrast thresholds', () => {
  assert.equal(checkTokens(manifest, css).length, 6);
  assert.equal(contrast('#000000', '#ffffff'), 21);
});

test('source drift and insufficient contrast fail the consistency check', () => {
  assert.throws(() => checkTokens(manifest, css.replace('--text: #1a2e1a', '--text: #888888')), /inventory differs/);
  const changed = structuredClone(manifest);
  changed.website.text = '#888888';
  assert.throws(() => checkTokens(changed, css.replace('--text: #1a2e1a', '--text: #888888')), /below 4.5/);
});

test('an explicitly supplied native source detects native palette drift', () => {
  const theme = Object.entries(manifest.native).map(([name, value]) => `${name}: '${value}'`).join('\n');
  assert.equal(checkTokens(manifest, css, theme).length, 6);
  assert.throws(() => checkTokens(manifest, css, theme.replace("textLight: '#666666'", "textLight: '#888888'")), /native color inventory differs/);
});
