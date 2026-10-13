(function(root) {
  'use strict';
  function today(now) {
    var parts = new Intl.DateTimeFormat('en-US', {timeZone: 'Atlantic/Azores', year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(now || new Date());
    var p = {};
    parts.forEach(function(part) { p[part.type] = part.value; });
    return p.year + '-' + p.month + '-' + p.day;
  }
  function add(date, days) {
    var d = new Date(date + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
  }
  function windowFor(range, now) {
    var start = today(now), days = {today: 1, tomorrow: 1, week: 7, month: 31, year: 365};
    if (range === 'tomorrow') start = add(start, 1);
    if (range === 'weekend') {
      var day = new Date(start + 'T12:00:00Z').getUTCDay();
      if (day !== 0 && day !== 6) start = add(start, 6 - day);
      return {start: start, end: add(start, day === 0 ? 1 : 2)};
    }
    return {start: start, end: range === 'all' ? null : add(start, days[range] || 7)};
  }
  function inRange(start, end, range, now) {
    if (!start) return false;
    var w = windowFor(range, now);
    return (end || start) >= w.start && (!w.end || start < w.end);
  }
  function normalize(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function matches(event, filters, now) {
    var tags = event.tags || [];
    return (!filters.savedOnly || (filters.savedIDs || []).indexOf(event.id) !== -1) &&
      (!filters.range || inRange(event.date, event.end_date, filters.range, now)) &&
      (!filters.kind || filters.kind === 'all' || (event.kind || 'event') === filters.kind) &&
      (!filters.locality || event.locality === filters.locality) &&
      (filters.tags || []).every(function(tag) { return tags.indexOf(tag) !== -1; }) &&
      (!filters.query || normalize([event.name, event.venue, event.description].join(' ')).indexOf(normalize(filters.query)) !== -1);
  }
  /** Return persisted bookmark IDs, or null when browser storage is unreadable. */
  function savedIDs(storage) {
    try {
      var saved = JSON.parse(storage.getItem('terceira-plans-v1') || '{}');
      if (!saved || Array.isArray(saved) || typeof saved !== 'object' || Object.keys(saved).some(function(id) { return !saved[id] || typeof saved[id].name !== 'string'; })) return null;
      return Object.keys(saved);
    } catch (error) { return null; }
  }
  var api = {today: today, add: add, windowFor: windowFor, inRange: inRange, normalize: normalize, matches: matches, savedIDs: savedIDs};
  if (typeof module !== 'undefined') module.exports = api;
  root.EventDiscovery = api;
})(typeof window === 'undefined' ? globalThis : window);
