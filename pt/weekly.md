---
layout: default
title: Eventos Semanais - Eventos da Terceira
description: Karaoke, noites de dança e outros eventos que se repetem todas as semanas em Angra do Heroísmo, Terceira.
permalink: /pt/weekly/
lang: pt
lang_alt: /weekly/
---

{% assign page_lang = page.lang | default: "en" %}
## Eventos Semanais

<p class="section-intro">Estes eventos acontecem todas as semanas em locais por Angra do Heroísmo. Confirma com cada local os horários em dias de feriado e possíveis alterações.</p>

{% for day in site.data.weekly %}
<div class="day-section">
  {%- assign day_label = day.day_pt | default: day.day -%}
  <div class="day-header">{{ day_label }}</div>
  <div class="day-events">
    {% for event in day.events %}
    {%- comment -%}
      Locale-aware field resolution. Each event may carry sibling
      `_pt`/`_en` fields, falling back to the bare field when missing.
    {%- endcomment -%}
    {% assign w_name = event.name_pt | default: event.name %}
    {% assign w_venue = event.venue_pt | default: event.venue %}
    {% assign w_address = event.address_pt | default: event.address %}
    {% assign w_description = event.description_pt | default: event.description %}
    {% assign w_note = event.note_pt | default: event.note %}
    {% assign map_link = "" %}
    {% if event.map_url %}
      {% assign map_link = event.map_url %}
    {% elsif w_address %}
      {% assign map_query = w_address | url_encode %}
      {% assign map_link = "https://www.google.com/maps/search/?api=1&query=" | append: map_query %}
    {% elsif w_venue %}
      {% assign map_query = w_venue | url_encode %}
      {% assign map_link = "https://www.google.com/maps/search/?api=1&query=" | append: map_query %}
    {% endif %}
    <div class="event-card">
      <div class="event-info">
        <div class="event-name">{{ w_name }}</div>
        <div class="event-venue">{{ w_venue }}</div>
        <div class="event-description">{{ w_description }}</div>
        {% if w_note %}
        <div class="event-note">{{ w_note }}</div>
        {% endif %}
        {% if w_address %}
        <div class="event-address">{{ w_address }}</div>
        {% endif %}
        {% if map_link != "" %}
        <a class="event-map-link" href="{{ map_link }}" target="_blank" rel="noopener">📍 Abrir no Maps</a>
        {% endif %}
        {% if event.instagram %}
        <a class="event-source" href="{{ event.instagram }}" target="_blank" rel="noopener">📸 Ver no Instagram</a>
        {% endif %}
        {% if event.url %}
        <a class="event-source" href="{{ event.url }}" target="_blank" rel="noopener">🌐 Website</a>
        {% endif %}
        <button type="button" class="event-flag-btn"
          data-event-name="{{ w_name | escape }}"
          data-event-date="{{ day_label }} (semanal)"
          data-event-venue="{{ w_venue | escape }}">
          🚩 Sugerir uma alteração
        </button>
      </div>
      <div class="event-time">{{ event.time }}</div>
    </div>
    {% endfor %}
  </div>
</div>
{% endfor %}
