---
layout: default
title: Event Archive
description: Past concerts, parties, festivals, and special nights in Angra do Heroísmo, Terceira.
lang_alt: /pt/archive/
---

## Event Archive

<p class="section-intro">Past concerts, parties, festivals, and special nights in Angra do Heroísmo.</p>

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
<p>No past events yet.</p>
{% endif %}

<p class="event-search-empty">
  No events match your search. Try different keywords or clear the filter.
</p>

<div class="archive-link-section">
  <a href="{{ '/special/' | relative_url }}" class="view-all">Back to Special Events</a>
</div>
