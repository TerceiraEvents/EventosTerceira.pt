---
layout: default
title: Events
description: Concerts, festivals, parties, and one-off events on Terceira.
lang_alt: /pt/special/
---

<h2>Events</h2>

<p class="section-intro">Concerts, festivals, parties, and one-off events on Terceira.</p>

{% include event_search_bar.html default_range="week" default_kind="events" %}

{% assign now_ts = "now" | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
{% assign sorted_events = site.data.special_events | sort: "date" %}

{% assign has_upcoming = false %}
{% for event in sorted_events %}
  {% assign event_ts = event.end_date | default: event.date | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
  {% if event_ts >= now_ts %}
    {% assign has_upcoming = true %}
  {% endif %}
{% endfor %}

{% if has_upcoming %}
{% for event in sorted_events %}
  {% assign event_ts = event.end_date | default: event.date | date: "%Y-%m-%d" | date: "%s" | plus: 0 %}
  {% if event_ts >= now_ts %}
    {% include special_event_card.html event=event %}
  {% endif %}
{% endfor %}
{% else %}
<p>No upcoming events at the moment. Check back soon!</p>
{% endif %}

<p class="event-search-empty">
  No events match your filters. Reset your filters or choose All upcoming to explore more dates.
</p>

<div class="archive-link-section">
  <a href="{{ '/archive/' | relative_url }}" class="view-all">Event Archive</a>
</div>

<p class="data-status">{% if page.lang == "pt" %}Página publicada em{% else %}Page built at{% endif %} {{ site.time | date_to_xmlschema }}. {% if page.lang == "pt" %}Esta hora não indica verificação pela organização.{% else %}This is not an organizer verification time.{% endif %}</p>
