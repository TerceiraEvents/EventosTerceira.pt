---
layout: default
title: Eventos da Terceira - O que se passa na Ilha Terceira
description: >-
  Noites de karaoke, concertos, festivais e eventos pontuais em Angra do
  Heroísmo e por toda a Ilha Terceira, Açores. Um guia comunitário curado
  todas as semanas.
permalink: /pt/
lang: pt
lang_alt: /
---

<div class="homepage-intro">
  <p class="intro-text">A Terceira é conhecida como a ilha dos Açores onde está sempre tudo a acontecer. <em>"São 8 ilhas e 1 parque de diversões, e a Terceira é o parque de diversões"</em> &mdash; é o que ouves dizer aos locais.</p>
  <p class="intro-text">Com touradas à corda, espectáculos musicais, festivais e muito mais, há quase sempre alguma coisa a acontecer. Mas se não és da ilha pode ser difícil perceberes-te de tudo.</p>
  <p class="intro-text">O propósito deste site é ajudar-te a saber o que se passa!</p>
</div>

<div class="homepage-buttons">
  <a href="{{ '/pt/weekly/' | relative_url }}" class="homepage-btn btn-weekly">
    <span class="btn-icon">&#127926;</span>
    <span class="btn-title">Eventos Semanais</span>
    <span class="btn-desc">Karaoke, noites de dança e outros eventos que se repetem todas as semanas</span>
  </a>
  <a href="{{ '/pt/special/' | relative_url }}" class="homepage-btn btn-special">
    <span class="btn-icon">&#127882;</span>
    <span class="btn-title">Eventos Especiais</span>
    <span class="btn-desc">Concertos, festivais, festas e eventos pontuais</span>
  </a>
  <a href="{{ '/pt/venues/' | relative_url }}" class="homepage-btn btn-venues">
    <span class="btn-icon">&#127963;</span>
    <span class="btn-title">Locais</span>
    <span class="btn-desc">Bares, restaurantes e espaços que recebem eventos pela Terceira</span>
  </a>
  <a href="{{ '/pt/resources/' | relative_url }}" class="homepage-btn btn-resources">
    <span class="btn-icon">&#128204;</span>
    <span class="btn-title">Outros Recursos</span>
    <span class="btn-desc">Bullfight Finder, páginas das câmaras municipais e muito mais</span>
  </a>
</div>

{%- comment -%}
  Build a list of upcoming special events (date >= today) and slice
  to the first 3, sorted ascending. Same `now_ts` / `event_ts` pattern
  as special.md / calendar.md so the cutoff is consistent. Translatable
  fields fall back to the bare field via `_pt`/`_en` siblings.
{%- endcomment -%}
{% assign now_ts = "now" | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
{% assign sorted_events = site.data.special_events | sort: "date" %}
{% assign upcoming_events = "" | split: "" %}
{% for event in sorted_events %}
  {% assign event_ts = event.date | date: "%s" | plus: 0 %}
  {% if event_ts >= now_ts %}
    {% assign upcoming_events = upcoming_events | push: event %}
  {% endif %}
{% endfor %}
{% assign upcoming_preview = upcoming_events | slice: 0, 3 %}

{% if upcoming_preview.size > 0 %}
<section class="home-events-preview">
  <h2 class="home-events-heading">Próximos eventos especiais</h2>
  <ul class="home-events-list">
    {% for event in upcoming_preview %}
      {% assign ev_name = event.name_pt | default: event.name %}
      {% assign ev_venue = event.venue_pt | default: event.venue %}
    <li class="home-events-item">
      <a href="{{ '/pt/special/' | relative_url }}">
        <span class="home-events-meta">
          <time class="home-events-date" datetime="{{ event.date | date: '%Y-%m-%d' }}">{{ event.date | date: "%-d %b" }}</time>
          {% if event.time %}<span class="home-events-time">{{ event.time }}</span>{% endif %}
        </span>
        <span class="home-events-title">{{ ev_name }}</span>
        {% if ev_venue %}<span class="home-events-venue">{{ ev_venue }}</span>{% endif %}
      </a>
    </li>
    {% endfor %}
  </ul>
  <a class="home-events-all" href="{{ '/pt/special/' | relative_url }}">Ver todos →</a>
</section>
{% endif %}

{% if site.posts.size > 0 %}
<section class="home-blog-preview">
  <h2 class="home-blog-heading">Do blogue</h2>
  <ul class="home-blog-list">
    {% for post in site.posts limit:3 %}
    <li class="home-blog-item">
      <a href="{{ post.url | relative_url }}">
        <span class="home-blog-meta">
          {% if post.category %}<span class="post-category post-category-{{ post.category }}">{{ post.category }}</span>{% endif %}
          <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%-d %b %Y" }}</time>
        </span>
        <span class="home-blog-title">{{ post.title }}</span>
      </a>
    </li>
    {% endfor %}
  </ul>
  <a class="home-blog-all" href="{{ '/pt/blog/' | relative_url }}">Todos os posts →</a>
</section>
{% endif %}
