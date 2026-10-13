(function() {
  'use strict';
  var pt = document.documentElement.lang === 'pt', prefix = pt ? '/pt' : '';
  function t(en, po) { return pt ? po : en; }
  document.querySelectorAll('.site-nav a').forEach(function(a) {
    if (a.hash || a.pathname !== location.pathname) return;
    if (/\/special\/$/.test(location.pathname)) {
      var onView = new URLSearchParams(location.search).get('kind') === 'exhibition';
      if ((new URLSearchParams(a.search).get('kind') === 'exhibition') !== onView) return;
    }
    a.setAttribute('aria-current', 'page');
  });
  function el(tag, text, parent) { var node = document.createElement(tag); if (text) node.textContent = text; if (parent) parent.appendChild(node); return node; }
  var records = [], data = document.getElementById('event-dataset');
  if (data) { try { records = JSON.parse(data.textContent); } catch (err) { el('p', t('Event data is unavailable. Reload this page to try again.', 'Dados indisponíveis. Recarrega a página para tentar novamente.'), document.querySelector('main')); } }
  function field(event, name) { return event[name + (pt ? '_pt' : '_en')] || event[name] || event[name + (pt ? '_en' : '_pt')] || ''; }
  function safeLink(url) { if (typeof url !== 'string' || !url.trim()) return null; try { var u = new URL(url, location.origin); return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null; } catch (err) { return null; } }
  function action(label, url, parent) { var href = safeLink(url); if (!href) return; var a = el('a',label,parent); a.className='detail-link'; a.href = href; a.rel = 'noopener'; return a; }
  function renderDetail() {
    var target = document.getElementById('event-detail'); if (!target) return;
    var id = new URLSearchParams(location.search).get('id'), event = records.find(function(e) { return e.id === id; });
    if (!event) { el('h2',t('Event unavailable','Evento indisponível'),target); el('p',t('This link does not match a published record. It has not opened another event.','Este link não corresponde a um registo publicado.'),target); action(t('Events','Eventos'),prefix+'/special/?range=all',target); return; }
    var name = field(event,'name'); document.title = name + ' | Terceira Events';
    el('h2',name,target);
    if ((event.end_date || event.date) < EventDiscovery.today()) el('p',t('This event has ended.','Este evento terminou.'),target);
    if (event.status === 'cancelled') el('p',t('Cancelled','Cancelado'),target);
    el('p',event.kind === 'exhibition' ? t('Exhibition','Exposição') : t('Dated event','Evento com data'),target);
    el('p',event.date + (event.end_date && event.end_date !== event.date ? ' – ' + event.end_date : '') + ' · Atlantic/Azores',target);
    el('p', event.kind === 'exhibition' ? (field(event,'visiting_hours') || t('Check visiting hours with the venue.','Confirma o horário de visita com o local.')) : (event.time || t('See details or check with the organizer for times.','Consulta os detalhes ou confirma os horários com a organização.')),target);
    el('p',field(event,'venue'),target); el('p',field(event,'address'),target);
    el('p',field(event,'price') || ((event.tags || []).includes('free') ? t('Free','Gratuito') : t('See details or check with the organizer for prices.','Consulta os detalhes ou confirma os preços com a organização.')),target);
    el('p',field(event,'description'),target);
    if (event.image_credit) el('p',t('Artwork: ','Cartaz: ') + event.image_credit,target);
    if (event.image_rights) el('p',event.image_rights,target);
    if (event.image_source) action(t('Artwork source','Fonte do cartaz'),event.image_source,target);
    if (event.organizer) el('p',t('Organizer: ','Organização: ') + field(event,'organizer'),target);
    (event.features || []).forEach(function(feature) { el('p',feature,target); });
    if (event.image) {
      var imageURL = safeLink(event.image); if (imageURL) { var img = el('img','',target); img.src=imageURL; img.alt=field(event,'image_alt') || name + t(' — organizer artwork',' — cartaz da organização'); img.loading='lazy'; img.addEventListener('error',function() { img.remove(); el('p',t('Artwork unavailable. Event information remains above.','Cartaz indisponível. A informação está acima.'),target); }); var artworkLink = action(t('Open full artwork','Abrir imagem completa'),imageURL,target); artworkLink.rel='noopener noreferrer'; }
    }
    var actions=el('div','',target); actions.className='detail-actions';
    action(t('Source','Fonte'),event.source_url || event.instagram,actions);
    action(t('Booking','Reservas'),event.booking_url,actions);
    action(t('Map','Mapa'),event.map_url,actions);
    var report=el('button',t('Suggest an edit','Sugerir uma alteração'),actions); report.type='button'; report.className='event-flag-btn'; report.dataset.eventName=name; report.dataset.eventDate=event.date; report.dataset.eventVenue=field(event,'venue');
    var share=el('button',t('Share link','Partilhar link'),actions); share.type='button';
    share.addEventListener('click',function() { var url=location.origin+prefix+'/events/?id='+encodeURIComponent(id); if (navigator.share) navigator.share({title:name,url:url}).catch(function() {}); else { var a=el('a',url,actions); a.href=url; } });
    var back=el('button',t('Back to results','Voltar aos resultados'),target); back.className='detail-link'; back.type='button'; back.addEventListener('click',function() { if (document.referrer && new URL(document.referrer).origin===location.origin && history.length>1) history.back(); else location.href=prefix+'/special/?range=all'; });
    action(t('Events','Eventos'),prefix+'/special/?range=all',target);
    var locale=document.querySelector('.locale-other'); if (locale) locale.href=(pt?'':'/pt')+'/events/?id='+encodeURIComponent(id);
  }
  renderDetail();
})();
