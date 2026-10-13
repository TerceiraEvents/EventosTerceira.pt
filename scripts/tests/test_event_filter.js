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
    attrs: {},
    setAttribute(key,value) { this.attrs[key]=value; },
    getAttribute(key) { return this.attrs[key] || null; },
    focus() { this.focused = true; },
    contains(node) { return node===this; },
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
  };
}

// Stub search bar + card sibling chain. withRange=false omits the range select.
function runPage({ cards, defaultRange = 'all', defaultKind = 'events', search = '', query = '', today = '2026-10-12', withRange = true, withKind = false, withTag = false, setRange = null, setKind = null, setTag = null, withFacets = false, withLocality = false, setFacets = null, setLocality = null, details = false, resetFilters = false, withNavigation = false, lang = 'en', escapeMenu = false, menuGeometry = null }) {
  const bar = {
    getBoundingClientRect() {return {bottom:240};},
    getAttribute: (k) => k === 'data-default-range' ? defaultRange : k === 'data-default-kind' ? defaultKind : null,
    parentElement: null,
    nextElementSibling: null,
    querySelector(sel) {
      if (sel === '.event-search-input') return input;
      if (sel === '.event-tags-menu') return withTag || withFacets ? tagMenu : null;
      if (sel === '.event-range-filter') return withRange ? rangeSelect : null;
      if (sel === '.event-kind-filter') return withKind ? kindSelect : null;
      if (sel === '.event-locality-filter') return withLocality ? localityMenu : null;
      if (sel === '.filter-reset') return reset;
      if (sel === '.result-count') return resultCount;
      return null;
    },
  };
  bar.querySelectorAll = selector => selector === '[data-facet]' ? (withFacets || withTag ? facets : []) : selector === '[data-locality]' ? (withLocality ? localities : []) : selector === '.filter-dropdown' ? [tagMenu, localityMenu] : [];
  const values = [...new Set(['free','kid-friendly','art',...Array.from(fs.readFileSync('_data/event_tags.yml','utf8').matchAll(/^\s*- slug:\s*([a-z-]+)\s*$/gm),match=>match[1])])];
  const facets = values.map(value => ({...stubElement(), value, checked:false, attrs:{'data-filter-label':value==='free'?(lang==='pt'?'Gratuito':'Free'):value==='kid-friendly'?(lang==='pt'?'Família':'Family'):value==='live-music'?(lang==='pt'?'Música ao Vivo':'Live Music'):value} }));
  const tagSummary = stubElement(), localitySummary = stubElement(), tagButton = stubElement(), localityButton = stubElement();
  const panel = {...stubElement(), getBoundingClientRect() { const anchor = menuGeometry ? (tagSummary.textContent.includes('Free') ? menuGeometry.selectedAnchor : menuGeometry.anchor) : 0; const left = this.style.left === undefined ? (menuGeometry.defaultLeft === undefined ? anchor : menuGeometry.defaultLeft) : anchor + parseFloat(this.style.left); return {left,right:left+menuGeometry.width,width:menuGeometry.width}; }};
  const tagMenu = {...stubElement(),getBoundingClientRect(){return {top:100};}, attrs:{'data-empty-label':lang==='pt'?'Etiquetas':'Tags'}, querySelector: selector=>selector==='summary'?tagButton:selector==='.filter-menu'?panel:tagSummary};
  const localityMenu = {...stubElement(),getBoundingClientRect(){return {top:150};}, querySelector:selector=>selector==='summary'?localityButton:selector==='.filter-menu'?panel:localitySummary};
  const localities=['','angra','praia','other'].map(value=>({...stubElement(), value, checked:!value, attrs:{'data-filter-label':value||(lang==='pt'?'Todos os locais':'All places')}}));
  const reset = stubElement(), resultCount = stubElement();
  const input = stubElement();
  input.value = query;
  const rangeSelect = stubElement();
  rangeSelect.value = defaultRange;
  const kindSelect = stubElement();
  kindSelect.value = defaultKind === 'exhibitions' ? 'exhibition' : defaultKind === 'all' ? 'all' : 'event';

  const cardNodes = cards.map((c) => ({
    attrs: {
      'data-event-id': c.id || '',
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
  const empty = stubElement(); empty.textContent = 'No events match your filters. Reset your filters or choose All upcoming.';
  const scope = {
    querySelector(selector) { return selector === '.event-search-empty' ? empty : null; },
  };
  bar.parentElement = scope;

  const TestDate = today ? class extends Date {
    constructor(...args) { super(...(args.length ? args : [`${today}T12:00:00Z`])); }
  } : Date;
  const locale = {href:'https://example.test/pt/special/'};
  const prefix = lang === 'pt' ? '/pt' : '';
  let currentURL = prefix + '/special/' + search;
  const listeners = {}, navHistory = [], popupHistory = [];
  const links = [['events', '/special/'], ['weekly', '/weekly/'], ['places', '/venues/']].map(([name, path]) => ({ name, ...Object.fromEntries(['pathname', 'search', 'hash'].map(key => [key, new URL(prefix + path, 'https://example.test')[key]])), attrs: {}, setAttribute(key, value) { this.attrs[key] = value; }, removeAttribute(key) { delete this.attrs[key]; } }));
  function recordNavigation() { if (withNavigation) navHistory.push(links.filter(link => link.attrs['aria-current'] === 'page').map(link => link.name)); }
  const sandbox = {
    Date: TestDate,
    window: { innerWidth:320, localStorage: new Proxy({}, {get() {throw new Error("Discovery must not access browser storage");}}), addEventListener(type, handler) { listeners[type] = handler; }, location: { search, pathname:prefix + '/special/', origin:'https://example.test' }, history:{replaceState(data,title,url) {currentURL=url; sandbox.window.location.search=new URL(url,'https://example.test').search;}}, __SITE_I18N: {} },
    URLSearchParams, Event: class { constructor(type) { this.type = type; } },
    document: {
      querySelectorAll: (sel) => sel === '.event-search-bar' ? [bar] : sel === '.site-nav a' ? links : [],
      querySelector: selector => selector === '.locale-other' ? locale : selector === '.event-search-bar' ? bar : null,
      createElement: () => stubElement(),
      documentElement:{lang,clientWidth:320},
      getElementById: key => ['event-detail','event-dataset'].includes(key) ? null : stubElement(),
      addEventListener(type, handler) { listeners[type] = handler; },
      dispatchEvent(event) { if (listeners[event.type]) listeners[event.type](event); },
    },
  };
  sandbox.localStorage = sandbox.window.localStorage;
  sandbox.location = sandbox.window.location;
  sandbox.URL = URL;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync('assets/js/discovery.js','utf8'), sandbox);
  sandbox.EventDiscovery = sandbox.window.EventDiscovery;
  vm.runInContext(FILTER_SRC, sandbox, { filename: 'event-filter.js' });
  if (withNavigation) vm.runInContext(fs.readFileSync('assets/js/event-details.js', 'utf8'), sandbox);
  recordNavigation();
  if(menuGeometry) { const menu=menuGeometry.menu==='places'?localityMenu:tagMenu; menu.open=true; for(const fn of menu.listeners.toggle || []) fn(); popupHistory.push(panel.getBoundingClientRect()); }

  if (setRange !== null && withRange) {
    rangeSelect.value = setRange;
    for (const fn of rangeSelect.listeners.change || []) fn();
    recordNavigation();
  }
  if (setKind !== null && withKind) {
    kindSelect.value = setKind;
    for (const fn of kindSelect.listeners.change || []) fn();
    recordNavigation();
  }
  if (setTag !== null && withTag) {
    for (const facet of facets) if (!['free','kid-friendly'].includes(facet.value)) facet.checked=facet.value===setTag;
    const chosen=facets.find(facet=>facet.value===setTag);
    if(chosen) for(const fn of chosen.listeners.change || []) fn();
  }
  if (setLocality !== null && withLocality) { for(const choice of localities) choice.checked=choice.value===setLocality; for(const fn of localities[0].listeners.change || []) fn(); }
  if (setFacets !== null && withFacets) { for (const facet of facets) if (!withTag || ['free','kid-friendly'].includes(facet.value)) facet.checked=setFacets.includes(facet.value); for (const fn of facets[0].listeners.change || []) fn(); }
  if (resetFilters) { for (const fn of reset.listeners.click || []) fn(); recordNavigation(); }
  if (escapeMenu) { tagMenu.open = true; for(const fn of tagMenu.listeners.keydown || []) fn({key:'Escape',preventDefault(){}}); }
  if(menuGeometry) popupHistory.push(panel.getBoundingClientRect());
  const visible = {};
  for (const card of cardNodes) visible[card.attrs['data-event-name']] = card.style.display !== 'none';
  return details ? {resetHidden:reset.hidden,visible,url:currentURL,localeHref:locale.href,resultCount:resultCount.textContent,emptyText:empty.textContent,navHistory,tagLabel:tagSummary.textContent,localityLabel:localitySummary.textContent,tagOpen:tagMenu.open,localityOpen:localityMenu.open,summaryFocused:tagButton.focused,popupTop:panel.style.top,popupBounds:menuGeometry?panel.getBoundingClientRect():null,popupHistory} : visible;
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
  assert.equal(page.resultCount,'1 result');
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

for (const lang of ['en','pt']) test(`actual ${lang} filter changes keep exactly one truthful current navigation link`,()=>{
 const page=runPage({cards:[{name:'Event',start:'2026-10-12',kind:'event'},{name:'Exhibition',start:'2026-10-01',end:'2026-12-31',kind:'exhibition'}],search:'?range=today',withKind:true,withNavigation:true,lang,setRange:'week',setKind:'exhibition',resetFilters:true,details:true});
 assert.deepEqual(page.navHistory,[['events'],['events'],['events'],['events']]);
 assert.equal(new URLSearchParams(page.url.split('?')[1]).get('range'),'all');
 assert.equal(new URLSearchParams(page.url.split('?')[1]).get('kind'),'event');
 assert.equal(new URLSearchParams(page.localeHref.split('?')[1]).get('kind'),'event');
});

for(const lang of ['en','pt']) test(`actual ${lang} compact Tags menu preserves topic plus Free/Family and URL/reset`,()=>{
 const cards=[{name:'All selected',start:daysFromToday(2),tags:'live-music free kid-friendly',locality:'angra'},{name:'Paid music',start:daysFromToday(2),tags:'live-music kid-friendly',locality:'angra'},{name:'Other topic',start:daysFromToday(2),tags:'free kid-friendly',locality:'angra'}];
 const options={cards,lang,withTag:true,withFacets:true,withLocality:true,withKind:true,search:'?tag=live-music&range=week',setFacets:['free','kid-friendly'],setLocality:'angra',details:true};
 const page=runPage(options);
 assert.deepEqual(page.visible,{'All selected':true,'Paid music':false,'Other topic':false});
 assert.equal(page.tagLabel,lang==='pt'?'Música ao Vivo + Gratuito + Família':'Live Music + Free + Family');
 const params=new URLSearchParams(page.url.split('?')[1]);
 assert.equal(params.get('tag'),'live-music');
 assert.deepEqual(params.get('tags').split(','),['free','kid-friendly']);
 assert.equal(params.get('locality'),'angra');
 assert.equal(new URLSearchParams(page.localeHref.split('?')[1]).get('tag'),'live-music');
 const restored=runPage({...options,search:'?'+params.toString(),setFacets:null,setLocality:null});
 assert.deepEqual(restored.visible,page.visible);
 assert.equal(restored.tagLabel,page.tagLabel);
 const reset=runPage({...options,resetFilters:true});
 assert.equal(reset.tagLabel,lang==='pt'?'Etiquetas':'Tags');
 assert.equal(reset.localityLabel,lang==='pt'?'Todos os locais':'All places');
 assert.deepEqual(reset.visible,{'All selected':true,'Paid music':true,'Other topic':true});
});

test('actual Tags Escape handler closes the popup and focuses its summary',()=>{
 const page=runPage({cards:[{name:'Event',start:daysFromToday(1)}],withFacets:true,escapeMenu:true,details:true});
 assert.equal(page.tagOpen,false);
 assert.equal(page.summaryFocused,true);
});

for(const geometry of [{menu:'places',anchor:29.796875,selectedAnchor:29.796875,defaultLeft:-120.6171875,width:256},{menu:'tags',anchor:158.390625,selectedAnchor:29.796875,width:256}]) test(`actual ${geometry.menu} popup is clamped after opening and summary wrapping`,()=>{
 const page=runPage({cards:[{name:'Event',start:daysFromToday(1),tags:'free kid-friendly'}],withFacets:true,withLocality:true,menuGeometry:geometry,setFacets:['free','kid-friendly'],details:true});
 for(const bounds of page.popupHistory) { assert(bounds.left>=0,JSON.stringify(bounds)); assert(bounds.right<=320,JSON.stringify(bounds)); }
});

for (const lang of ['en','pt']) test(`actual ${lang} reset is absent at defaults and available only for active filters`,()=>{
 const options={cards:[{name:'Event',start:'2026-10-12',kind:'event',tags:'free'}],defaultRange:'week',withKind:true,withFacets:true,withLocality:true,details:true,lang};
 assert.equal(runPage(options).resetHidden,true);
 for(const change of [{query:'Event'},{setRange:'today'},{setKind:'exhibition'},{setFacets:['free']},{setLocality:'angra'}]) {
  assert.equal(runPage({...options,...change}).resetHidden,false);
  assert.equal(runPage({...options,...change,resetFilters:true}).resetHidden,true);
 }
});

test('actual reset clears combined query, tags, locality and date and closes menus',()=>{
 const page=runPage({cards:[{name:'MONTE',start:'2026-10-12',kind:'event',tags:'free kid-friendly',locality:'angra'},{name:'Other',start:'2026-10-13',kind:'event'}],defaultRange:'week',withKind:true,withFacets:true,withLocality:true,query:'MONTE',setFacets:['free','kid-friendly'],setLocality:'praia',setRange:'today',resetFilters:true,details:true});
 assert.deepEqual(page.visible,{MONTE:true,Other:true});
 assert.equal(page.url,'/special/?range=week&kind=event');
 assert.equal(page.resetHidden,true);
 assert.equal(page.tagOpen,false);
 assert.equal(page.localityOpen,false);
});

test('opened filter popup begins below the entire control panel so Reset remains exposed',()=>{
 const page=runPage({cards:[{name:'Event',start:'2026-10-12',kind:'event'}],withFacets:true,withLocality:true,menuGeometry:{anchor:30,width:200,viewport:320},details:true});
 assert.equal(page.popupTop,'146px');
});
