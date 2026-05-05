---
layout: default
title: Full Events Calendar
description: Full calendar of upcoming concerts, festivals, parties, and one-off events in Angra do Heroísmo, Terceira.
lang_alt: /pt/calendar/
---

<h2>Full Special Events Calendar</h2>

<p class="section-intro">All upcoming concerts, festivals, parties, and one-off events in Angra do Heroísmo. Narrow by date range, search, or tag.</p>

{% include event_search_bar.html default_range="all" %}

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
<p>No upcoming events at the moment. Check back soon!</p>
{% endif %}

<p class="event-search-empty">
  No events match your filters. Try a different range, search, or tag.
</p>

<div class="archive-link-section">
  <a href="{{ '/archive' | relative_url }}" class="view-all">Event Archive</a>
</div>
