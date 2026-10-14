import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { checkTokens, contrast } from '../check_discovery_tokens.mjs';
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

function reservationColors(state) {
  const selectors = new Map([
    ['a', 1], ['main a', 2], ['.venue-card a', 11], ['.event-reservations a', 11],
    ['.venue-card .event-reservations a', 21],
  ]);
  for (const [selector, specificity] of [...selectors]) {
    if (state !== 'normal') selectors.set(`${selector}:${state}`, specificity + 10);
  }
  const values = new Map();
  for (const rule of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const applicable = rule[1].trim().split(',').map(selector => selectors.get(selector.trim())).filter(value => value !== undefined);
    if (!applicable.length) continue;
    const specificity = Math.max(...applicable);
    for (const declaration of rule[2].matchAll(/(?:^|;)\s*(color|background)\s*:\s*([^;]+)/g)) {
      const [, property, value] = declaration;
      if (!values.has(property) || values.get(property).specificity <= specificity) values.set(property, {specificity, value: value.trim()});
    }
  }
  return Object.fromEntries([...values].map(([property, {value}]) => [property, value.replace(/var\(--([^)]*)\)/g, (_, token) => manifest.website[token])]));
}

for (const state of ['normal', 'hover', 'visited', 'focus', 'focus-visible']) {
  test(`reservation link text retains contrast through the source cascade: ${state}`, () => {
    const {color, background} = reservationColors(state);
    assert.ok(contrast(color, background) >= 4.5, `${state}: ${color}/${background} has contrast ${contrast(color, background).toFixed(2)}`);
    assert.equal(color, manifest.website.white);
  });
}
