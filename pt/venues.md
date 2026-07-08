---
layout: default
title: Locais
description: Bares, restaurantes, espaços culturais e outros locais que recebem eventos pela Terceira.
permalink: /pt/venues/
lang: pt
lang_alt: /venues/
---

{% assign page_lang = page.lang | default: "en" %}
<h2>Locais</h2>

<p class="section-intro">Bares, restaurantes, espaços culturais e outros locais que recebem eventos pela Terceira.</p>

{%- comment -%}
  Mantém os slugs e a ordem em sintonia com `venues.md` (EN). Qualquer
  `category` desconhecida (ou em falta) cai em "outros" e é renderizada
  no fim.
{%- endcomment -%}
{% assign category_slugs = "arts-culture,food-drink,nightlife,sports-outdoor,civic,other" | split: "," %}
{% assign category_labels_pt = "Arte e Cultura,Comida e Bebida,Bares e Vida Noturna,Desporto e Ar Livre,Cívico,Outros" | split: "," %}

{% for category_slug in category_slugs %}
  {%- if category_slug == "other" -%}
    {%- assign category_venues = "" | split: "," -%}
    {%- for venue in site.data.venues -%}
      {%- assign vc = venue.category | default: "other" -%}
      {%- unless category_slugs contains vc and vc != "other" -%}
        {%- assign category_venues = category_venues | push: venue -%}
      {%- endunless -%}
    {%- endfor -%}
  {%- else -%}
    {%- assign category_venues = site.data.venues | where: "category", category_slug -%}
  {%- endif -%}
  {%- if category_venues.size == 0 -%}{%- continue -%}{%- endif -%}
  {%- assign category_label = category_labels_pt[forloop.index0] -%}

<h3 class="venue-category" id="category-{{ category_slug }}">{{ category_label }}</h3>

{% for venue in category_venues %}
{% assign v_name = venue.name_pt | default: venue.name %}
{% assign v_address = venue.address_pt | default: venue.address %}
{% assign v_description = venue.description_pt | default: venue.description %}
{% assign v_description_after = venue.description_after_weekly_pt | default: venue.description_after_weekly %}
{% assign v_reservation_label = venue.reservation_label_pt | default: venue.reservation_label %}
<div class="venue-card">
  <h3>{{ v_name }}</h3>
  <div class="venue-address">{{ v_address }}{% if venue.map_url %} · <a href="{{ venue.map_url }}">Mapa</a>{% endif %}</div>
  <div class="venue-regulars">
    {% if v_description %}
    <p>{{ v_description }}</p>
    {% endif %}
    {% if venue.weekly %}
    <p><strong>Horário semanal:</strong></p>
    <ul>
      {% for entry in venue.weekly %}{% assign day_str = entry.day | strip %}{% assign day_len = day_str | size | minus: 1 %}{% assign day_last = day_str | slice: day_len, 1 %}
        {%- assign entry_day = entry.day_pt | default: entry.day -%}
        {%- assign entry_name = entry.name_pt | default: entry.name -%}
      <li><strong>{{ entry_day }}</strong>{% if day_last == ":" %} {{ entry_name }}{% else %} — {{ entry_name }}{% endif %}</li>
      {% endfor %}
    </ul>
    {% endif %}
    {% if v_description_after %}
    <p>{{ v_description_after }}</p>
    {% endif %}
    {% if venue.links or venue.reservation_phone %}
    <p>{% if venue.links %}{% for link in venue.links %}{% unless forloop.first %} · {% endunless %}{%- assign link_label = link.label_pt | default: link.label -%}<a href="{{ link.url }}">{{ link_label }}</a>{% endfor %}{% endif %}{% if venue.links and venue.reservation_phone %} · {% endif %}{% if venue.reservation_phone %}Reservas: {{ venue.reservation_phone }}{% endif %}</p>
    {% endif %}
    {% if venue.reservation_url %}
    <div class="event-reservations"><a href="{{ venue.reservation_url }}">{{ v_reservation_label | default: "Reservar uma mesa" }}</a></div>
    {% endif %}
  </div>
</div>

{%- comment -%}
  JSON-LD `LocalBusiness` (or more specific subtype) per venue card.
  Same logic as the EN page, but with the locale-resolved name and
  address. `addressCountry` is always "PT" via `_includes/postal_address.html`.
{%- endcomment -%}

{%- assign schema_type = venue.schema_type | default: "LocalBusiness" -%}
{%- assign sameas_buf = "" -%}
{%- assign business_url = "" -%}
{%- if venue.links -%}
  {%- for link in venue.links -%}
    {%- assign link_url = link.url | strip -%}
    {%- unless link_url contains "mailto:" or link_url == "" -%}
      {%- assign sameas_buf = sameas_buf | append: link_url | append: "|||" -%}
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
{% endfor %}
