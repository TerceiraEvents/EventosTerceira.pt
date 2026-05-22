---
layout: default
title: Contribuir
description: Como contribuir para os Eventos da Terceira. Sugere um local, corrige um evento ou ajuda a fazer crescer o projeto.
permalink: /pt/contribute/
lang: pt
lang_alt: /contribute/
---

<div class="homepage-intro">
  <h2 style="border:none; padding:0; margin-bottom:0.75rem;">Queres adicionar o teu espaço ou evento?</h2>
  <p class="intro-text">Não há critérios para entrar &mdash; se quiseres aparecer aqui, fixe, adicionamos!</p>
</div>

<div class="homepage-buttons" style="max-width:580px;">
  <a href="{{ '/pt/suggest/' | relative_url }}" class="homepage-btn btn-weekly">
    <span class="btn-icon">&#128221;</span>
    <span class="btn-title">Enviar uma Sugestão</span>
    <span class="btn-desc">Preenche o formulário e nós tratamos do resto</span>
  </a>
  <a href="#use-the-app" class="homepage-btn btn-special">
    <span class="btn-icon">&#128241;</span>
    <span class="btn-title">Usa a App</span>
    <span class="btn-desc">Toca em "Sugerir Evento" na app móvel</span>
  </a>
  <a href="https://github.com/TerceiraEvents/EventosTerceira.pt" class="homepage-btn btn-venues" target="_blank" rel="noopener">
    <span class="btn-icon">&#128187;</span>
    <span class="btn-title">Abrir um PR</span>
    <span class="btn-desc">Submete alterações no GitHub (se gostas de código)</span>
  </a>
  <a href="https://www.instagram.com/chrisrackauckas/" class="homepage-btn btn-resources" target="_blank" rel="noopener">
    <span class="btn-icon">&#128242;</span>
    <span class="btn-title">Manda DM ao Chris</span>
    <span class="btn-desc">Manda mensagem no Instagram @chrisrackauckas</span>
  </a>
</div>

<h2 id="use-the-app">Sugerir um Evento a partir da App</h2>

<p class="section-intro">A maneira mais fácil de pôr um evento aqui no site é pela app. Descarrega aqui:</p>

{% include app_store_badges.html %}

<div class="venue-card">
  <div class="venue-regulars">
    <ol>
      <li>Abre a app <strong>Eventos da Terceira</strong> no telemóvel (<a href="https://apps.apple.com/us/app/terceira-events/id6766769428">iOS</a> / <a href="https://play.google.com/store/apps/details?id=com.terceiraevents.app">Android</a>)</li>
      <li>No ecrã principal, toca em <strong>Sugerir Evento</strong></li>
      <li>Preenche o formulário &mdash; só o nome do evento, a data e o local são obrigatórios</li>
      <li>Opcionalmente acrescenta a hora, morada, link do Google Maps, descrição, link de Instagram e o teu nome (para créditos)</li>
      <li>Toca em <strong>Enviar</strong></li>
    </ol>
    <p>A tua sugestão vai diretamente para a fila de revisão. Assim que confirmarmos, aparece no site e na app automaticamente.</p>
  </div>
</div>

<h2>Abrir um Pull Request</h2>

<p class="section-intro">Se já trabalhas com GitHub, podes submeter alterações diretamente. É o caminho mais rápido porque saltas a fila de revisão &mdash; o teu PR aparece logo que for integrado.</p>

<div class="venue-card">
  <h3>Para um Evento Especial</h3>
  <div class="venue-regulars">
    <p>Acrescenta uma entrada em <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/special_events.yml"><code>_data/special_events.yml</code></a>:</p>
<pre><code>- date: 2026-06-15
  name: "Concerto no Teatro Angrense"
  venue: Teatro Angrense
  address: Rua da Esperan&ccedil;a 48-52, Angra do Hero&iacute;smo
  map_url: https://maps.app.goo.gl/...
  time: "21:30"
  description: "M&uacute;sica ao vivo com convidado especial."
  instagram: https://www.instagram.com/p/...
  tags:
    - live-music
    - kid-friendly
</code></pre>
    <p>Só <code>date</code>, <code>name</code> e <code>venue</code> são obrigatórios. O campo <code>date</code> tem de estar em formato YYYY-MM-DD.</p>
    <p>O campo <code>address</code> é a morada legível mostrada no cartão. O <code>map_url</code> é um link de partilha do Google Maps opcional (por exemplo, <code>maps.app.goo.gl/...</code>) que alimenta o botão &quot;Abrir no Maps&quot; &mdash; usa-o quando queres marcar uma localização exata. Se omitires <code>map_url</code>, o botão recorre a uma pesquisa do Google Maps pela morada.</p>
    <p>Adiciona uma lista <code>tags</code> para ajudar quem visita a filtrar o calendário. As etiquetas disponíveis estão definidas em <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/event_tags.yml"><code>_data/event_tags.yml</code></a>: <code>kid-friendly</code>, <code>live-music</code>, <code>cinema</code>, <code>theater</code>, <code>dance</code>, <code>nightlife</code>, <code>karaoke</code>, <code>food-drink</code>, <code>exhibition</code>, <code>literature</code>, <code>workshop</code>, <code>free</code>, <code>outdoor</code>, <code>bullfighting</code>.</p>
  </div>
</div>

<div class="venue-card">
  <h3>Para um Evento Semanal Recorrente</h3>
  <div class="venue-regulars">
    <p>Acrescenta uma entrada em <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/weekly.yml"><code>_data/weekly.yml</code></a> no dia certo:</p>
<pre><code>- day: Wednesday
  events:
    - name: Karaoke Night
      venue: Tasca do Cam&otilde;es
      time: "20:30"
      description: Karaoke semanal no Cam&otilde;es
      address: Rua Da Rocha 64, Angra do Hero&iacute;smo
</code></pre>
  </div>
</div>

<div class="venue-card">
  <h3>Para um Local Novo</h3>
  <div class="venue-regulars">
    <p>Edita <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/venues.md"><code>venues.md</code></a> e acrescenta um novo bloco <code>venue-card</code> seguindo o padrão existente. Inclui a morada, um link de pesquisa no Google Maps, uma descrição e quaisquer redes sociais relevantes.</p>
  </div>
</div>

<h2>Contactar Diretamente</h2>

<p class="section-intro">Não és fã de formulários nem de GitHub? Também serve.</p>

<div class="venue-card">
  <div class="venue-regulars">
    <ul>
      <li><strong>DM no Instagram</strong> &mdash; <a href="https://www.instagram.com/chrisrackauckas/">@chrisrackauckas</a></li>
      <li><strong>Em pessoa</strong> &mdash; encontras o Chris nas noites de karaoke. Vais perceber qual.</li>
    </ul>
    <p>Manda um cartaz, uma descrição, uma data aproximada, o que tiveres. A gente dá conta.</p>
  </div>
</div>

<h2>O Que Aceitamos</h2>

<div class="venue-card">
  <div class="venue-regulars">
    <p>Praticamente tudo o que se passa na Terceira: concertos, festivais, touradas, noites de karaoke, festas de dança, lançamentos de livros, teatro, sessões de cinema, exposições, workshops, eventos desportivos e tudo o que houver pelo meio.</p>
    <p>Tanto Angra do Heroísmo como a Praia da Vitória &mdash; e qualquer outro sítio da ilha.</p>
    <p>Eventos em português ou em inglês são igualmente bem-vindos. Se quiseres divulgar os eventos semanais do teu espaço, também adicionamos.</p>
  </div>
</div>
