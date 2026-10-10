'use strict';
// Client-side range filter keeps overlapping events. Loads the actual
// event-search script from _layouts/default.html and drives it through
// a stub DOM. Run from the repo root:  node --test scripts/tests/test_event_filter.js

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function loadFilterScript() {
  const layout = fs.readFileSync('_layouts/default.html', 'utf8');
  const blocks = [...layout.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  const src = blocks.find((b) => b.includes('inRange'));
  assert.ok(src, 'event-search script block found in default.html');
  return src;
}
const FILTER_SRC = loadFilterScript();

function fmt(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function daysFromToday(n) {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + n);
  return fmt(d);
}

function stubElement() {
  const listeners = {};
  return {
    listeners,
    value: '',
    style: {},
    textContent: '',
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
  };
}

// Stub search bar + card sibling chain. withRange=false omits the range select.
function runPage({ cards, defaultRange = 'all', search = '', withRange = true, setRange = null }) {
  const bar = {
    getAttribute: (k) => (k === 'data-default-range' ? defaultRange : null),
    parentElement: null,
    nextElementSibling: null,
    querySelector(sel) {
      if (sel === '.event-search-input') return input;
      if (sel === '.event-tag-filter') return null;
      if (sel === '.event-range-filter') return withRange ? rangeSelect : null;
      return null;
    },
  };
  const input = stubElement();
  const rangeSelect = stubElement();
  rangeSelect.value = defaultRange;

  const cardNodes = cards.map((c) => ({
    attrs: {
      'data-event-name': c.name,
      'data-event-date': c.start,
      ...(c.end === 'missing' ? {} : { 'data-event-end-date': c.end || c.start }),
      'data-event-venue': '',
      'data-event-description': '',
      'data-event-tags': '',
    },
    style: {},
    classList: { contains: (cls) => cls === 'special-event' },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
    querySelectorAll() { return []; },
  }));

  let node = bar;
  for (const card of cardNodes) {
    node.nextElementSibling = card;
    card.nextElementSibling = null;
    node = card;
  }
  const scope = {
    querySelector() { return null; },
  };
  bar.parentElement = scope;

  const sandbox = {
    window: { location: { search }, __SITE_I18N: {} },
    URLSearchParams,
    document: {
      querySelectorAll: (sel) => (sel === '.event-search-bar' ? [bar] : []),
      querySelector: () => null,
      getElementById: () => stubElement(),
      addEventListener() {},
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(FILTER_SRC, sandbox, { filename: 'event-filter.js' });

  if (setRange !== null && withRange) {
    rangeSelect.value = setRange;
    for (const fn of rangeSelect.listeners.change || []) fn();
  }
  const visible = {};
  for (const card of cardNodes) visible[card.attrs['data-event-name']] = card.style.display !== 'none';
  return visible;
}

const ONGOING = { name: 'ongoing', start: daysFromToday(-5), end: daysFromToday(5) };
const ENDED = { name: 'ended', start: daysFromToday(-10), end: daysFromToday(-1) };
const ENDS_TODAY = { name: 'ends-today', start: daysFromToday(-3), end: daysFromToday(0) };
const PAST_SINGLE = { name: 'past-single', start: daysFromToday(-2), end: daysFromToday(-2) };
const FUTURE_WEEK = { name: 'future-week', start: daysFromToday(2), end: daysFromToday(2) };
const FUTURE_MONTH = { name: 'future-month', start: daysFromToday(20), end: daysFromToday(20) };
const FUTURE_FAR = { name: 'future-far', start: daysFromToday(40), end: daysFromToday(40) };
const NULL_DATE = { name: 'null-date', start: null, end: null };

test('week range keeps overlapping events and drops the rest', () => {
  const v = runPage({
    cards: [ONGOING, ENDED, ENDS_TODAY, PAST_SINGLE, FUTURE_WEEK, FUTURE_FAR, NULL_DATE],
    setRange: 'week',
  });
  assert.equal(v.ongoing, true, 'ongoing exhibition overlaps the week');
  assert.equal(v['ends-today'], true, 'event ending today is still upcoming');
  assert.equal(v['future-week'], true, 'single event inside the week');
  assert.equal(v['null-date'], true, 'undated cards stay visible');
  assert.equal(v.ended, false, 'event ended yesterday is hidden');
  assert.equal(v['past-single'], false, 'past single event is hidden');
  assert.equal(v['future-far'], false, 'event beyond the week horizon is hidden');
});

test('month range horizon overlaps start dates', () => {
  const v = runPage({ cards: [FUTURE_MONTH, FUTURE_FAR, ONGOING], setRange: 'month' });
  assert.equal(v['future-month'], true, 'event inside the month');
  assert.equal(v.ongoing, true, 'ongoing exhibition overlaps the month');
  assert.equal(v['future-far'], false, 'event beyond the month horizon is hidden');
});

test('all range keeps everything not yet ended', () => {
  const v = runPage({ cards: [ONGOING, ENDED, ENDS_TODAY, FUTURE_FAR], setRange: 'all' });
  assert.equal(v.ongoing, true, 'ongoing visible under all');
  assert.equal(v['ends-today'], true, 'end-today visible under all');
  assert.equal(v['future-far'], true, 'far future visible under all');
  assert.equal(v.ended, false, 'ended event hidden even under all');
});

test('pages without a range select skip range filtering', () => {
  const v = runPage({ cards: [ONGOING, ENDED, PAST_SINGLE], withRange: false });
  assert.equal(v.ongoing, true, 'ongoing visible');
  assert.equal(v.ended, true, 'past events stay on archive-like pages');
  assert.equal(v['past-single'], true, 'past single stays');
});

test('range from URL seed applies on load', () => {
  const v = runPage({ cards: [FUTURE_WEEK, FUTURE_FAR], search: '?range=week' });
  assert.equal(v['future-week'], true, 'in-week event visible');
  assert.equal(v['future-far'], false, 'out-of-week event hidden');
});

test('cards without an end-date attribute fall back to start', () => {
  const v = runPage({
    cards: [
      { name: 'future-no-end-attr', start: daysFromToday(2), end: 'missing' },
      { name: 'past-no-end-attr', start: daysFromToday(-2), end: 'missing' },
    ],
    setRange: 'week',
  });
  assert.equal(v['future-no-end-attr'], true, 'future card without end attr visible');
  assert.equal(v['past-no-end-attr'], false, 'past card without end attr hidden');
});
