---
layout: default
title: Eventos Especiais
description: Concertos, festivais, festas e eventos pontuais desta semana em Angra do Heroísmo, Terceira.
permalink: /pt/special/
lang: pt
lang_alt: /special/
---

<h2>Eventos Especiais</h2>

<p class="section-intro">Concertos, festivais, festas e eventos pontuais em Angra do Heroísmo. Usa o intervalo de datas, a pesquisa ou a etiqueta para refinares a lista.</p>

{% include event_search_bar.html default_range="week" %}

{% assign now_ts = "now" | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
{% assign sorted_events = site.data.special_events | sort: "date" %}

{% assign has_upcoming = false %}
{% for event in sorted_events %}
  {% assign event_ts = event.date | date: "%s" | plus: 0 %}
  {% if event_ts >= now_ts %}
    {% assign has_upcoming = true %}
  {% endif %}
{% endfor %}

{% if has_upcoming %}
{% for event in sorted_events %}
  {% assign event_ts = event.date | date: "%s" | plus: 0 %}
  {% if event_ts >= now_ts %}
    {% include special_event_card.html event=event %}
  {% endif %}
{% endfor %}
{% else %}
<p>De momento não há eventos agendados. Volta a passar por aqui em breve!</p>
{% endif %}

<p class="event-search-empty">
  Nenhum evento corresponde aos filtros. Tenta um intervalo, pesquisa ou etiqueta diferentes.
</p>

<div class="archive-link-section">
  <a href="{{ '/pt/archive/' | relative_url }}" class="view-all">Arquivo de Eventos</a>
</div>
