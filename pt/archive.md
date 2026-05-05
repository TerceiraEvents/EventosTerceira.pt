---
layout: default
title: Arquivo de Eventos
description: Concertos, festas, festivais e noites especiais já realizados em Angra do Heroísmo, Terceira.
permalink: /pt/archive/
lang: pt
lang_alt: /archive/
---

## Arquivo de Eventos

<p class="section-intro">Concertos, festas, festivais e noites especiais já realizados em Angra do Heroísmo.</p>

{% include event_search_bar.html %}

{% assign now_ts = "now" | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
{% assign sorted_events = site.data.special_events | sort: "date" | reverse %}

{% assign has_past = false %}
{% for event in sorted_events %}
  {% assign event_ts = event.date | date: "%s" | plus: 0 %}
  {% if event_ts < now_ts %}
    {% assign has_past = true %}
  {% endif %}
{% endfor %}

{% if has_past %}
{% for event in sorted_events %}
  {% assign event_ts = event.date | date: "%s" | plus: 0 %}
  {% if event_ts < now_ts %}
    {% include special_event_card.html event=event %}
  {% endif %}
{% endfor %}
{% else %}
<p>Ainda não há eventos no arquivo.</p>
{% endif %}

<p class="event-search-empty">
  Nenhum evento corresponde à pesquisa. Tenta outras palavras ou limpa o filtro.
</p>

<div class="archive-link-section">
  <a href="{{ '/pt/special/' | relative_url }}" class="view-all">Voltar a Eventos Especiais</a>
</div>
