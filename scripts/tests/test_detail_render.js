const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function render({lang = 'pt', records, id = 'exhibition-one', stored = null, unavailableStorage = false}) {
  const handlers = {}, roots = [];
  let storageAccesses = 0;
  function node(tag) {
    return {tag, textContent:'', children:[], dataset:{}, attrs:{}, listeners:{}, className:'',
      appendChild(child) { this.children.push(child); child.parent=this; },
      replaceChildren() { this.children=[]; },
      remove() {this.parent.children=this.parent.children.filter(child=>child!==this);},
      setAttribute(key,value) {this.attrs[key]=value;},
      addEventListener(type,handler) {this.listeners[type]=handler;},
      click() {if(this.listeners.click) this.listeners.click(); if(handlers.click) handlers.click({target:this});},
    };
  }
  const main=node('main'), detail=node('div'),  locale=node('a');
  main.appendChild(detail); roots.push(main,locale);
  function all() {const result=[]; function visit(n) {result.push(n); n.children.forEach(visit);} roots.forEach(visit); return result;}
  function matches(n,selector) {return selector==='main' ? n===main : selector.startsWith('.') ? n.className.split(' ').includes(selector.slice(1)) : false;}
  const document={documentElement:{lang},referrer:'',createElement:node,
    querySelector(selector) {if(selector==='.locale-other')return locale; return all().find(n=>matches(n,selector)) || null;},
    querySelectorAll(selector) {return all().filter(n=>matches(n,selector));},
    getElementById(key) {return {'event-detail':detail,'event-dataset':{textContent:JSON.stringify(records)}}[key] || null;},
    addEventListener(type,handler) {handlers[type]=handler;},
    dispatchEvent(event) {if (handlers[event.type]) handlers[event.type](event);},
  };
  const localStorage={getItem() {storageAccesses++; if(unavailableStorage)throw new Error('denied'); return stored;}, setItem(key,value) {storageAccesses++; if(unavailableStorage)throw new Error('denied'); stored=value;},removeItem() {storageAccesses++; if(unavailableStorage)throw new Error('denied'); stored=null;}};
  const context={document,localStorage,window:{addEventListener(){}},location:{origin:'https://eventosterceira.pt',pathname:lang==='pt'?'/pt/events/':'/events/',search:'?id='+id},navigator:{},Event,history:{length:1},URL,URLSearchParams,EventDiscovery:require('../../assets/js/discovery.js')};
  vm.runInNewContext(fs.readFileSync('assets/js/event-details.js','utf8'),context);
  return {all, detail, stored:()=>stored, locale, storageAccesses:()=>storageAccesses};
}
const exhibition={id:'exhibition-one',kind:'exhibition',date:'2026-10-01',end_date:'2026-12-31',name:'Exhibition',name_pt:'Exposição',visiting_hours:'16:00 to 18:30 during the published programme period',visiting_hours_pt:'das 16h00 às 18h30 durante o período anunciado'};

test('actual PT detail render selects published Portuguese visiting hours',()=>{
  const page=render({records:[exhibition]});
  const text=page.detail.children.map(n=>n.textContent);
  assert(text.includes(exhibition.visiting_hours_pt));
  assert(!text.includes(exhibition.visiting_hours));
});
test('actual PT share fallback preserves locale and exact identity',()=>{
  const page=render({records:[exhibition]});
  page.all().find(n=>n.textContent==='Partilhar link').click();
  assert(page.all().some(n=>n.href==='https://eventosterceira.pt/pt/events/?id=exhibition-one'));
});
test('missing scalar fields do not deny times or prices in the published programme',()=>{
 const event={id:'exhibition-one',kind:'event',date:'2026-10-30',end_date:'2026-10-31',name:'Published programme',description:'30 October opens at 18:00; 31 October opens at 12:00. Tickets cost €3.'};
 const page=render({lang:'en',records:[event]});
 const text=page.detail.children.map(n=>n.textContent);
 assert(!text.includes('Time not published.'));
 assert(!text.includes('Price not published.'));
 assert(text.includes(event.description));
 assert(text.includes('See details or check with the organizer for times.'));
 assert(text.includes('See details or check with the organizer for prices.'));
});

test('actual navigation script marks exactly the matching discovery destination in EN/PT',()=>{
 for(const prefix of ['', '/pt']) for(const [query,expected] of [['?kind=exhibition&range=all','events'],['?range=today&q=music','events'],['?kind=event&free=1','events'],['?kind=event&range=today','events'],['?kind=exhibition&range=today','events']]) {
  const links=[['events',prefix+'/special/'],['weekly',prefix+'/weekly/'],['places',prefix+'/venues/']].map(([name,path])=>({name,...Object.fromEntries(['pathname','search'].map(key=>[key,new URL(path,'https://eventosterceira.pt')[key]])),attrs:{},setAttribute(key,value){this.attrs[key]=value;},removeAttribute(key){delete this.attrs[key];}}));
  const document={documentElement:{lang:prefix?'pt':'en'},createElement:()=>({setAttribute:()=>{}}),dispatchEvent:()=>{},querySelectorAll:selector=>selector==='.site-nav a'?links:[],querySelector:()=>null,getElementById:key=>key==='event-dataset'?{textContent:'[]'}:null,addEventListener:()=>{}};
  vm.runInNewContext(fs.readFileSync('assets/js/event-details.js','utf8'),{document,window:{addEventListener(){}},localStorage:{getItem:()=>null},location:{origin:'https://eventosterceira.pt',pathname:prefix+'/special/',search:query},Event,URL,URLSearchParams});
  assert.deepEqual(links.filter(link=>link.attrs['aria-current']==='page').map(link=>link.name),[expected]);
 }
});


const artworkFixtures=JSON.parse(fs.readFileSync('scripts/tests/fixtures/artwork/events.json','utf8')).events;
test('shared artwork fixtures expose complete localized alt and recorded provenance',()=>{
 for(const lang of ['en','pt']) for(const shape of ['portrait','landscape','oversized']) {
  const record=artworkFixtures.find(event=>event.id==='artwork-fixture-'+shape);
  const page=render({lang,records:[record],id:record.id});
  const image=page.all().find(node=>node.tag==='img');
  assert.equal(image.src,new URL(record.image,'https://eventosterceira.pt').href);
  assert.equal(image.alt,record['image_alt_'+lang]);
  assert(page.all().some(node=>node.textContent.includes('CC0-1.0')));
  assert(page.all().some(node=>node.href===record.image_source));
  assert(page.all().some(node=>node.textContent.includes(record.image_credit)));
 }
});
test('unavailable artwork retains the exact event and its detail actions in EN/PT',()=>{
 for(const lang of ['en','pt']) {
  const record=artworkFixtures.find(event=>event.id==='artwork-fixture-unavailable');
  const page=render({lang,records:[record],id:record.id});
  page.all().find(node=>node.tag==='img').listeners.error();
  assert(!page.all().some(node=>node.tag==='img'));
  assert(page.all().some(node=>node.textContent.includes(lang==='pt'?'Cartaz indisponível':'Artwork unavailable')));
  assert(page.all().some(node=>node.textContent===record[lang==='pt'?'name_pt':'name']));
  assert(page.all().some(node=>node.textContent===(lang==='pt'?'Partilhar link':'Share link')));
  assert(page.all().some(node=>node.textContent===(lang==='pt'?'Partilhar link':'Share link')));
 }
});
test('missing and malformed shared artwork do not create unsafe image controls',()=>{
 for(const shape of ['missing','malformed']) {
  const record=artworkFixtures.find(event=>event.id==='artwork-fixture-'+shape);
  const page=render({records:[record],id:record.id});
  assert(!page.all().some(node=>node.tag==='img'));
  assert(!page.all().some(node=>String(node.href).startsWith('javascript:')));
  assert(page.all().some(node=>node.textContent==='Partilhar link'));
 }
});
test('shared poster has a safe localized full-size link independent of its source page',()=>{
 for(const lang of ['en','pt']) {
  const record={...artworkFixtures[0],image_source:'https://example.org/organizer-page'};
  const page=render({lang,records:[record],id:record.id});
  const link=page.all().find(node=>node.textContent===(lang==='pt'?'Abrir imagem completa':'Open full artwork'));
  assert(link);
  assert.equal(link.href,new URL(record.image,'https://eventosterceira.pt').href);
  assert.equal(link.className,'detail-link');
  assert.equal(link.rel,'noopener noreferrer');
 }
});

test('corrupt encoded fixture keeps event and full-size action after the decoder error',()=>{
 const record=artworkFixtures.find(event=>event.id==='artwork-fixture-corrupt-encoded');
 const page=render({lang:'en',records:[record],id:record.id});
 const image=page.all().find(node=>node.tag==='img');
 assert(image.src.endsWith('/corrupt-encoded.png'));
 image.listeners.error();
 assert(!page.all().some(node=>node.tag==='img'));
 assert(page.all().some(node=>node.textContent===record.name));
 assert(page.all().some(node=>node.textContent==='Share link'));
 assert(page.all().some(node=>node.textContent==='Open full artwork'));
});

test('actual EN/PT detail has no browser saving and never accesses stored data',()=>{
 for(const lang of ['en','pt']) {
  const page=render({lang,records:[exhibition],stored:'{"retained":{"name":"Existing bookmark"}}'});
  assert.equal(page.storageAccesses(),0);
  assert(!page.all().some(node=>node.dataset.saveId || node.className==='save-event'));
  assert.equal(page.stored(),'{"retained":{"name":"Existing bookmark"}}');
 }
});
