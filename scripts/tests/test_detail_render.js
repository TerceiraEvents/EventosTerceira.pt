const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function render({lang = 'pt', records, id = 'exhibition-one', stored = null, unavailableStorage = false}) {
  const handlers = {}, roots = [];
  function node(tag) {
    return {tag, textContent:'', children:[], dataset:{}, attrs:{}, listeners:{}, className:'',
      appendChild(child) { this.children.push(child); child.parent=this; },
      replaceChildren() { this.children=[]; },
      setAttribute(key,value) {this.attrs[key]=value;},
      addEventListener(type,handler) {this.listeners[type]=handler;},
      closest(selector) {return selector==='[data-save-id]' && this.dataset.saveId ? this : null;},
      click() {if(this.listeners.click) this.listeners.click(); if(handlers.click) handlers.click({target:this});},
    };
  }
  const main=node('main'), detail=node('div'), saved=node('div'), locale=node('a');
  main.appendChild(detail); main.appendChild(saved); roots.push(main,locale);
  function all() {const result=[]; function visit(n) {result.push(n); n.children.forEach(visit);} roots.forEach(visit); return result;}
  function matches(n,selector) {return selector==='main' ? n===main : selector==='[data-save-id]' ? !!n.dataset.saveId : selector.startsWith('.') ? n.className.split(' ').includes(selector.slice(1)) : false;}
  const document={documentElement:{lang},referrer:'',createElement:node,
    querySelector(selector) {if(selector==='.locale-other')return locale; return all().find(n=>matches(n,selector)) || null;},
    querySelectorAll(selector) {return all().filter(n=>matches(n,selector));},
    getElementById(key) {return {'event-detail':detail,'saved-events':saved,'event-dataset':{textContent:JSON.stringify(records)}}[key] || null;},
    addEventListener(type,handler) {handlers[type]=handler;},
  };
  const localStorage={getItem() {if(unavailableStorage)throw new Error('denied'); return stored;}, setItem(key,value) {if(unavailableStorage)throw new Error('denied'); stored=value;},removeItem() {if(unavailableStorage)throw new Error('denied'); stored=null;}};
  const context={document,localStorage,location:{origin:'https://eventosterceira.pt',pathname:lang==='pt'?'/pt/events/':'/events/',search:'?id='+id},navigator:{},history:{length:1},URL,URLSearchParams,EventDiscovery:require('../../assets/js/discovery.js')};
  vm.runInNewContext(fs.readFileSync('assets/js/plans.js','utf8'),context);
  return {all, detail, stored:()=>stored, locale};
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
test('invalid saved data has explicit recovery without silently overwriting it',()=>{
  const page=render({lang:'en',records:[exhibition],stored:'[1,2]'});
  assert(page.all().some(n=>n.textContent.includes('Saved data is unreadable')));
  page.all().find(n=>n.dataset.saveId==='exhibition-one').click();
  assert.equal(page.stored(),'[1,2]');
  page.all().find(n=>n.textContent==='Clear unreadable saved data').click();
  assert.equal(page.stored(),null);
});
test('actual storage denial remains distinct from malformed saved data',()=>{
 const page=render({lang:'en',records:[exhibition],unavailableStorage:true});
 assert(page.all().some(n=>n.textContent.includes('Browser storage is unavailable')));
 assert(!page.all().some(n=>n.textContent.includes('Saved data is unreadable')));
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
test('unreadable saved data cannot make Save appear persistently pressed',()=>{
 const page=render({lang:'en',records:[exhibition],stored:'[1,2]'});
 const button=page.all().find(n=>n.dataset.saveId==='exhibition-one');
 button.click();
 assert.equal(button.attrs['aria-pressed'],'false');
 assert.equal(button.disabled,true);
 assert.equal(page.stored(),'[1,2]');
});
