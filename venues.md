---
layout: default
title: Venues - Terceira Events
description: Bars, restaurants, cultural spaces, and other venues hosting events in Angra do Heroísmo, Terceira.
lang_alt: /pt/venues/
---

{% assign page_lang = page.lang | default: "en" %}
{%- if page_lang == "pt" -%}
<h2>Locais</h2>

<p class="section-intro">Bares, restaurantes, espaços culturais e outros locais que recebem eventos em Angra do Heroísmo.</p>
{%- else -%}
<h2>Venues</h2>

<p class="section-intro">Bars, restaurants, cultural spaces, and other venues hosting events in Angra do Heroísmo.</p>
{%- endif -%}

{% for venue in site.data.venues %}
{%- if page_lang == "pt" -%}
  {% assign v_name = venue.name_pt | default: venue.name %}
  {% assign v_address = venue.address_pt | default: venue.address %}
  {% assign v_description = venue.description_pt | default: venue.description %}
  {% assign v_description_after = venue.description_after_weekly_pt | default: venue.description_after_weekly %}
  {% assign v_reservation_label = venue.reservation_label_pt | default: venue.reservation_label %}
{%- else -%}
  {% assign v_name = venue.name_en | default: venue.name %}
  {% assign v_address = venue.address_en | default: venue.address %}
  {% assign v_description = venue.description_en | default: venue.description %}
  {% assign v_description_after = venue.description_after_weekly_en | default: venue.description_after_weekly %}
  {% assign v_reservation_label = venue.reservation_label_en | default: venue.reservation_label %}
{%- endif -%}
<div class="venue-card">
  <h3>{{ v_name }}</h3>
  <div class="venue-address">{{ v_address }}{% if venue.map_url %} · <a href="{{ venue.map_url }}">{% if page_lang == "pt" %}Mapa{% else %}Map{% endif %}</a>{% endif %}</div>
  <div class="venue-regulars">
    {% if v_description %}
    <p>{{ v_description }}</p>
    {% endif %}
    {% if venue.weekly %}
    <p><strong>{% if page_lang == "pt" %}Horário semanal:{% else %}Weekly schedule:{% endif %}</strong></p>
    <ul>
      {% for entry in venue.weekly %}{% assign day_str = entry.day | strip %}{% assign day_len = day_str | size | minus: 1 %}{% assign day_last = day_str | slice: day_len, 1 %}
        {%- if page_lang == "pt" -%}
          {%- assign entry_day = entry.day_pt | default: entry.day -%}
          {%- assign entry_name = entry.name_pt | default: entry.name -%}
        {%- else -%}
          {%- assign entry_day = entry.day_en | default: entry.day -%}
          {%- assign entry_name = entry.name_en | default: entry.name -%}
        {%- endif -%}
      <li><strong>{{ entry_day }}</strong>{% if day_last == ":" %} {{ entry_name }}{% else %} — {{ entry_name }}{% endif %}</li>
      {% endfor %}
    </ul>
    {% endif %}
    {% if v_description_after %}
    <p>{{ v_description_after }}</p>
    {% endif %}
    {% if venue.links or venue.reservation_phone %}
    <p>{% if venue.links %}{% for link in venue.links %}{% unless forloop.first %} · {% endunless %}{%- if page_lang == "pt" -%}{%- assign link_label = link.label_pt | default: link.label -%}{%- else -%}{%- assign link_label = link.label_en | default: link.label -%}{%- endif -%}<a href="{{ link.url }}">{{ link_label }}</a>{% endfor %}{% endif %}{% if venue.links and venue.reservation_phone %} · {% endif %}{% if venue.reservation_phone %}{% if page_lang == "pt" %}Reservas{% else %}Reservations{% endif %}: {{ venue.reservation_phone }}{% endif %}</p>
    {% endif %}
    {% if venue.reservation_url %}
      {%- if page_lang == "pt" -%}
        {%- assign default_reservation_label = "Reservar uma mesa" -%}
      {%- else -%}
        {%- assign default_reservation_label = "Make a dinner reservation" -%}
      {%- endif -%}
    <div class="event-reservations"><a href="{{ venue.reservation_url }}">{{ v_reservation_label | default: default_reservation_label }}</a></div>
    {% endif %}
  </div>
</div>

{%- comment -%}
  JSON-LD `LocalBusiness` (or more specific subtype) per venue card.
  Address: parsed into `PostalAddress` when a Portuguese 9700-/9760-
  postal code is present; otherwise the raw address string becomes
  the `addressLocality`. `addressCountry` is always "PT".
  `sameAs` collects every URL from `links` (no mailto, etc.).
{%- endcomment -%}

{%- assign schema_type = venue.schema_type | default: "LocalBusiness" -%}
{%- comment -%}
  Build sameAs from venue.links, and pull out a "Website" link as the
  business's canonical URL if one exists. Liquid 4.0.4 lacks `push`
  so sameAs is built as a delimited string then split back. Trailing
  delimiter is fine — Liquid's `split` drops the empty trailing element.
{%- endcomment -%}
{%- assign sameas_buf = "" -%}
{%- assign business_url = "" -%}
{%- if venue.links -%}
  {%- for link in venue.links -%}
    {%- assign link_url = link.url | strip -%}
    {%- unless link_url contains "mailto:" or link_url == "" -%}
      {%- assign sameas_buf = sameas_buf | append: link_url | append: "|||" -%}
      {%- comment -%} First "Website" link wins. {%- endcomment -%}
      {%- if business_url == "" and link.label == "Website" -%}
        {%- assign business_url = link_url -%}
      {%- endif -%}
    {%- endunless -%}
  {%- endfor -%}
{%- endif -%}
{%- assign sameas = sameas_buf | split: "|||" -%}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": {{ schema_type | jsonify }},
  "name": {{ v_name | jsonify }},
  "address": {% include postal_address.html address=v_address %}{% if business_url != "" %},
  "url": {{ business_url | jsonify }}{% endif %}{% if venue.map_url %},
  "hasMap": {{ venue.map_url | jsonify }}{% endif %}{% if venue.telephone %},
  "telephone": {{ venue.telephone | jsonify }}{% endif %}{% if sameas.size > 0 %},
  "sameAs": {{ sameas | jsonify }}{% endif %}
}
</script>
{% endfor %}
