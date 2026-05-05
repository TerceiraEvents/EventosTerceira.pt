---
layout: default
title: Weekly Events
description: Karaoke, dance nights, and other recurring events happening every week in Angra do Heroísmo, Terceira.
lang_alt: /pt/weekly/
---

{% assign page_lang = page.lang | default: "en" %}
## Weekly Events

<p class="section-intro">These events happen every week at venues around Angra do Heroísmo. Check with venues for holiday schedules and changes.</p>

{% for day in site.data.weekly %}
<div class="day-section">
  {%- if page_lang == "pt" -%}
    {%- assign day_label = day.day_pt | default: day.day -%}
  {%- else -%}
    {%- assign day_label = day.day_en | default: day.day -%}
  {%- endif -%}
  <div class="day-header">{{ day_label }}</div>
  <div class="day-events">
    {% for event in day.events %}
    {%- comment -%}
      Locale-aware field resolution. Weekly entries can carry sibling
      `_pt`/`_en` fields the same way special events do.
    {%- endcomment -%}
    {%- if page_lang == "pt" -%}
      {% assign w_name = event.name_pt | default: event.name %}
      {% assign w_venue = event.venue_pt | default: event.venue %}
      {% assign w_address = event.address_pt | default: event.address %}
      {% assign w_description = event.description_pt | default: event.description %}
      {% assign w_note = event.note_pt | default: event.note %}
    {%- else -%}
      {% assign w_name = event.name_en | default: event.name %}
      {% assign w_venue = event.venue_en | default: event.venue %}
      {% assign w_address = event.address_en | default: event.address %}
      {% assign w_description = event.description_en | default: event.description %}
      {% assign w_note = event.note_en | default: event.note %}
    {%- endif -%}
    {%- comment -%}
      Build a Google Maps link, falling back map_url > address > venue.
      Same logic as `_includes/special_event_card.html` so weekly and
      special events present location identically.
    {%- endcomment -%}
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
        <a class="event-map-link" href="{{ map_link }}" target="_blank" rel="noopener">📍 {% if page_lang == "pt" %}Abrir no Maps{% else %}Open in Maps{% endif %}</a>
        {% endif %}
        {% if event.instagram %}
        <a class="event-source" href="{{ event.instagram }}" target="_blank" rel="noopener">📸 {% if page_lang == "pt" %}Ver no Instagram{% else %}View on Instagram{% endif %}</a>
        {% endif %}
        {% if event.url %}
        <a class="event-source" href="{{ event.url }}" target="_blank" rel="noopener">🌐 {% if page_lang == "pt" %}Website{% else %}Website{% endif %}</a>
        {% endif %}
        <button type="button" class="event-flag-btn"
          data-event-name="{{ w_name | escape }}"
          data-event-date="{{ day_label }} ({% if page_lang == 'pt' %}semanal{% else %}weekly{% endif %})"
          data-event-venue="{{ w_venue | escape }}">
          🚩 {% if page_lang == "pt" %}Sugerir uma alteração{% else %}Suggest an edit{% endif %}
        </button>
      </div>
      <div class="event-time">{{ event.time }}</div>
    </div>
    {% endfor %}
  </div>
</div>
{% endfor %}
