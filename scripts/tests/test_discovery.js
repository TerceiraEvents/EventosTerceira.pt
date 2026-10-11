const {test} = require('node:test');
const assert = require('node:assert/strict');
const d = require('../../assets/js/discovery.js');
test('island midnight and DST use Azores calendar date independently of device', () => {
  for (const [instant, day] of [['2026-01-01T00:30:00Z','2025-12-31'],['2026-01-01T01:00:00Z','2026-01-01'],['2026-03-29T00:30:00Z','2026-03-28'],['2026-03-29T01:30:00Z','2026-03-29'],['2026-10-25T00:30:00Z','2026-10-25']]) assert.equal(d.today(new Date(instant)),day);
});
test('shortcuts have inclusive days and exclusive horizons', () => {
 const now = new Date('2026-10-12T12:00:00Z');
 assert.deepEqual(d.windowFor('weekend',now),{start:'2026-10-17',end:'2026-10-19'});
 assert.equal(d.inRange('2026-10-13',null,'today',now),false);
 assert.equal(d.inRange('2026-10-13',null,'tomorrow',now),true);
 assert.equal(d.inRange('2026-10-19',null,'week',now),false);
 assert.equal(d.inRange('2026-09-01','2026-12-31','today',now),true);
 assert.deepEqual(d.windowFor('weekend',new Date('2026-10-18T12:00:00Z')),{start:'2026-10-18',end:'2026-10-19'});
});
test('all selected tags and locality combine with accent-insensitive query', () => {
 const event = {date:'2026-10-12',name:'Música em família',tags:['free','kid-friendly'],locality:'angra'};
 const filters = {range:'today',query:'musica',tags:['free','kid-friendly'],locality:'angra'};
 const now = new Date('2026-10-12T12:00:00Z');
 assert.equal(d.matches(event,filters,now),true);
 assert.equal(d.matches({...event,locality:undefined},filters,now),false);
 assert.equal(d.matches({...event,tags:['kid-friendly']},filters,now),false);
});
test('detail actions reject absent values and executable URLs', () => {
 const fs=require('node:fs'), vm=require('node:vm');
 const src=fs.readFileSync('assets/js/plans.js','utf8');
 const fn=src.slice(src.indexOf('function safeLink'),src.indexOf('function action'));
 const safe=vm.runInNewContext('('+fn.trim()+')',{URL,location:{origin:'https://eventosterceira.pt'}});
 for (const value of [undefined,null,'','  ','javascript:alert(1)','data:text/html,hello']) assert.equal(safe(value),null);
 assert.equal(safe('https://example.com/tickets'),'https://example.com/tickets');
});
