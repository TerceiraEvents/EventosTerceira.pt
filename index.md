---
layout: default
title: Terceira Events
lang_alt: /pt/
---

<div class="homepage-intro">
  <p class="intro-text">Terceira is known as the island in the Azores where everything is happening. <em>"There are 8 islands and 1 amusement park, and Terceira is the amusement park"</em> is what you'll hear the locals say.</p>
  <p class="intro-text">With bull fights, musical shows, festivals, and more, there's almost always something going on. But if you're not from the island it can be difficult to figure it all out.</p>
  <p class="intro-text">The purpose of this site is to help you figure out everything that's going on!</p>
</div>

<div class="homepage-buttons">
  <a href="{{ '/weekly/' | relative_url }}" class="homepage-btn btn-weekly">
    <span class="btn-icon">&#127926;</span>
    <span class="btn-title">Weekly Events</span>
    <span class="btn-desc">Karaoke, dance nights, and other recurring events happening every week</span>
  </a>
  <a href="{{ '/special/' | relative_url }}" class="homepage-btn btn-special">
    <span class="btn-icon">&#127882;</span>
    <span class="btn-title">Special Events</span>
    <span class="btn-desc">Concerts, festivals, parties, and one-off events</span>
  </a>
  <a href="{{ '/venues/' | relative_url }}" class="homepage-btn btn-venues">
    <span class="btn-icon">&#127963;</span>
    <span class="btn-title">Venues</span>
    <span class="btn-desc">Bars, restaurants, and spaces hosting events around Terceira</span>
  </a>
  <a href="{{ '/resources/' | relative_url }}" class="homepage-btn btn-resources">
    <span class="btn-icon">&#128204;</span>
    <span class="btn-title">Other Resources</span>
    <span class="btn-desc">Bullfight Finder, city event pages, and more</span>
  </a>
</div>

<section class="app-store-section" aria-labelledby="get-the-app">
  <h2 id="get-the-app">Get the Terceira Events app</h2>
  <p>Browse events on the go and suggest new ones in one tap.</p>
  {% include app_store_badges.html %}
</section>

{%- comment -%}
  Build a list of upcoming special events (date >= today) and slice
  to the first 3, sorted ascending. Same `now_ts` / `event_ts` pattern
  as special.md / calendar.md so the cutoff is consistent.
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
  <h2 class="home-events-heading">Upcoming special events</h2>
  <ul class="home-events-list">
    {% for event in upcoming_preview %}
    <li class="home-events-item">
      <a href="{{ '/special/' | relative_url }}">
        <span class="home-events-meta">
          <time class="home-events-date" datetime="{{ event.date | date: '%Y-%m-%d' }}">{{ event.date | date: "%-d %b" }}</time>
          {% if event.time %}<span class="home-events-time">{{ event.time }}</span>{% endif %}
        </span>
        <span class="home-events-title">{{ event.name }}</span>
        {% if event.venue %}<span class="home-events-venue">{{ event.venue }}</span>{% endif %}
      </a>
    </li>
    {% endfor %}
  </ul>
  <a class="home-events-all" href="{{ '/special/' | relative_url }}">All upcoming →</a>
</section>
{% endif %}

{% if site.posts.size > 0 %}
<section class="home-blog-preview">
  <h2 class="home-blog-heading">From the blog</h2>
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
  <a class="home-blog-all" href="{{ '/blog/' | relative_url }}">All posts →</a>
</section>
{% endif %}
