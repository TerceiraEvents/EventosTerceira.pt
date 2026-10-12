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
  const src = blocks.find((b) => b.includes("document.querySelectorAll('.event-search-bar')"));
  assert.ok(src, 'event-search script block found in default.html');
  return src;
}
const FILTER_SRC = loadFilterScript();

function daysFromToday(n) {
  const d = new Date('2026-10-12T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0,10);
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
function runPage({ cards, defaultRange = 'all', defaultKind = 'events', search = '', query = '', today = '2026-10-12', withRange = true, withKind = false, withTag = false, setRange = null, setKind = null, setTag = null, withFacets = false, withLocality = false, setFacets = null, setLocality = null, details = false, resetFilters = false }) {
  const bar = {
    getAttribute: (k) => k === 'data-default-range' ? defaultRange : k === 'data-default-kind' ? defaultKind : null,
    parentElement: null,
    nextElementSibling: null,
    querySelector(sel) {
      if (sel === '.event-search-input') return input;
      if (sel === '.event-tag-filter') return withTag ? tagSelect : null;
      if (sel === '.event-range-filter') return withRange ? rangeSelect : null;
      if (sel === '.event-kind-filter') return withKind ? kindSelect : null;
      if (sel === '.event-locality-filter') return withLocality ? localitySelect : null;
      if (sel === '.filter-reset') return reset;
      if (sel === '.result-count') return resultCount;
      return null;
    },
  };
  bar.querySelectorAll = () => withFacets ? facets : [];
  const facets = ['free','kid-friendly'].map(value => ({...stubElement(), value, checked:false}));
  const localitySelect = stubElement(), reset = stubElement(), resultCount = stubElement();
  const input = stubElement();
  input.value = query;
  const tagSelect = stubElement();
  tagSelect.value = '';
  tagSelect.options = ['', 'free', 'kid-friendly', 'art'].map(value => ({value}));
  const rangeSelect = stubElement();
  rangeSelect.value = defaultRange;
  const kindSelect = stubElement();
  kindSelect.value = defaultKind === 'exhibitions' ? 'exhibition' : defaultKind === 'all' ? 'all' : 'event';

  const cardNodes = cards.map((c) => ({
    attrs: {
      'data-event-name': c.name,
      'data-event-date': c.start,
      ...(c.end === 'missing' ? {} : { 'data-event-end-date': c.end || c.start }),
      'data-event-venue': c.venue || '',
      'data-event-locality': c.locality || '',
      'data-event-description': c.description || '',
      ...(c.kind === undefined ? {} : { 'data-event-kind': c.kind }),
      'data-event-tags': c.tags || '',
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

  const TestDate = today ? class extends Date {
    constructor(...args) { super(...(args.length ? args : [`${today}T12:00:00Z`])); }
  } : Date;
  const locale = {href:'https://example.test/pt/special/'};
  let currentURL = '/special/'+search;
  const sandbox = {
    Date: TestDate,
    window: { location: { search, pathname:'/special/' }, history:{replaceState(data,title,url) {currentURL=url;}}, __SITE_I18N: {} },
    URLSearchParams,
    document: {
      querySelectorAll: (sel) => (sel === '.event-search-bar' ? [bar] : []),
      querySelector: selector => selector === '.locale-other' ? locale : null,
      documentElement:{lang:'en'},
      getElementById: () => stubElement(),
      addEventListener() {},
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync('assets/js/discovery.js','utf8'), sandbox);
  sandbox.EventDiscovery = sandbox.window.EventDiscovery;
  vm.runInContext(FILTER_SRC, sandbox, { filename: 'event-filter.js' });

  if (setRange !== null && withRange) {
    rangeSelect.value = setRange;
    for (const fn of rangeSelect.listeners.change || []) fn();
  }
  if (setKind !== null && withKind) {
    kindSelect.value = setKind;
    for (const fn of kindSelect.listeners.change || []) fn();
  }
  if (setTag !== null && withTag) {
    tagSelect.value = setTag;
    for (const fn of tagSelect.listeners.change || []) fn();
  }
  if (setLocality !== null && withLocality) { localitySelect.value=setLocality; for (const fn of localitySelect.listeners.change || []) fn(); }
  if (setFacets !== null && withFacets) { for (const facet of facets) facet.checked=setFacets.includes(facet.value); for (const fn of facets[0].listeners.change || []) fn(); }
  if (resetFilters) for (const fn of reset.listeners.click || []) fn();
  const visible = {};
  for (const card of cardNodes) visible[card.attrs['data-event-name']] = card.style.display !== 'none';
  return details ? {visible,url:currentURL,localeHref:locale.href,resultCount:resultCount.textContent} : visible;
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

test('kind, range, tag, and search filters combine across inclusive ranges', () => {
  const cases = [
    {
      name: 'default events keep an event ending today and hide exhibitions',
      cards: [
        { name: 'today event', start: daysFromToday(-2), end: daysFromToday(0), kind: 'event', tags: 'music' },
        { name: 'on view', start: daysFromToday(-10), end: daysFromToday(10), kind: 'exhibition', tags: 'exhibition' },
      ], withKind: true, withRange: true, setRange: 'week',
      expected: { 'today event': true, 'on view': false },
    },
    {
      name: 'URL kind selects an overlapping year-crossing exhibition with matching search',
      cards: [
        { name: 'Winter exhibition', start: '2026-12-31', end: '2027-01-02', kind: 'exhibition', tags: 'exhibition art' },
        { name: 'Winter event', start: '2026-12-31', end: '2027-01-02', kind: 'event', tags: 'art' },
      ], withKind: true, withRange: true, search: '?q=winter&kind=exhibition', today: '2026-10-11',
      defaultKind: 'events',
      expected: { 'Winter exhibition': true, 'Winter event': false },
    },
    {
      name: 'ended exhibition is excluded by upcoming range and kind all still honors range',
      cards: [
        { name: 'ended display', start: '2026-08-01', end: '2026-10-10', kind: 'exhibition', tags: 'exhibition' },
        { name: 'ongoing display', start: '2026-06-12', end: '2026-12-31', kind: 'exhibition', tags: 'exhibition' },
      ], withKind: true, withTag: true, withRange: true, setKind: 'all', setTag: 'exhibition', setRange: 'week', today: '2026-10-11',
      expected: { 'ended display': false, 'ongoing display': true },
    },
    {
      name: 'kind all includes the default event record when no kind attribute exists',
      cards: [
        { name: 'legacy event', start: daysFromToday(1), end: daysFromToday(1), tags: 'music' },
        { name: 'display', start: daysFromToday(1), end: daysFromToday(3), kind: 'exhibition', tags: 'exhibition' },
      ], withKind: true, withTag: true, withRange: true, setKind: 'all', setTag: 'music', setRange: 'week', query: 'legacy',
      expected: { 'legacy event': true, display: false },
    },
  ];
  for (const scenario of cases) {
    const { name, expected, ...options } = scenario;
    assert.deepEqual(runPage(options), expected, name);
  }
});

test('Today excludes tomorrow and visitor timezone does not widen the window', () => {
  const result = runPage({cards:[{name:'Tomorrow',start:'2026-10-13'}],today:'2026-10-12',setRange:'today'});
  assert.equal(result.Tomorrow, false);
});

test('actual page uses AND for both facets, locality and accented search',()=>{
  const cards=[
    {name:'Música em família',start:'2026-10-12',tags:'free kid-friendly',locality:'angra'},
    {name:'Música paid',start:'2026-10-12',tags:'kid-friendly',locality:'angra'},
    {name:'Música elsewhere',start:'2026-10-12',tags:'free kid-friendly',locality:'praia'},
    {name:'Música unknown',start:'2026-10-12',tags:'free kid-friendly'},
  ];
  const page=runPage({cards,query:'musica',withFacets:true,withLocality:true,setFacets:['free','kid-friendly'],setLocality:'angra',details:true});
  assert.deepEqual(page.visible,{'Música em família':true,'Música paid':false,'Música elsewhere':false,'Música unknown':false});
  assert.equal(page.resultCount,'1 results');
});
test('actual page shares and restores range kind tags locality search and locale',()=>{
  const cards=[{name:'Música',start:'2026-10-13',kind:'event',tags:'free kid-friendly',locality:'angra'},{name:'Another exhibition',start:'2026-10-13',kind:'exhibition',tags:'free kid-friendly',locality:'angra'}];
  const options={cards,withFacets:true,withLocality:true,withKind:true,details:true};
  const page=runPage({...options,query:'musica',setRange:'tomorrow',setKind:'event',setFacets:['free','kid-friendly'],setLocality:'angra'});
  const params=new URLSearchParams(page.url.split('?')[1]);
  assert.equal(params.get('range'),'tomorrow');
  assert.equal(params.get('kind'),'event');
  assert.equal(params.get('tags'),'free,kid-friendly');
  assert.equal(params.get('locality'),'angra');
  assert.equal(params.get('q'),'musica');
  assert.equal(page.localeHref,'https://example.test/pt'+page.url);
  const restored=runPage({...options,search:'?'+params.toString()});
  assert.deepEqual(restored.visible,page.visible);
  assert.equal(restored.url,page.url);
});
test('actual page respects all and exhibition defaults and restores them on reset',()=>{
  const cards=[{name:'Event',start:'2026-10-13',kind:'event'},{name:'Exhibition',start:'2026-10-13',kind:'exhibition'}];
  assert.deepEqual(runPage({cards,withKind:true,defaultKind:'all'}),{Event:true,Exhibition:true});
  const page=runPage({cards,withKind:true,defaultKind:'exhibitions',defaultRange:'month',setKind:'event',setRange:'today',resetFilters:true,details:true});
  assert.deepEqual(page.visible,{Event:false,Exhibition:true});
  assert.equal(new URLSearchParams(page.url.split('?')[1]).get('kind'),'exhibition');
  assert.equal(new URLSearchParams(page.url.split('?')[1]).get('range'),'month');
});
