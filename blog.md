---
layout: default
title: Blog
description: News, guides, and stories about life on Terceira, from venue reopenings to favourite food spots and tips for newcomers.
permalink: /blog/
lang_alt: /pt/blog/
---

<h2>Blog</h2>

<p class="section-intro">News, guides, and stories about life on Terceira — from reopening announcements to favourite food spots and tips for newcomers.</p>

{%- comment -%}
  Filter to EN posts only. Posts without a `lang:` field are
  treated as English (the default for posts authored before the
  bilingual launch). PT posts have `lang: pt` and a permalink
  under `/pt/blog/...` so they show on `/pt/blog/` instead.
{%- endcomment -%}
{%- assign posts_for_locale = site.posts | where_exp: "post", "post.lang == nil or post.lang == 'en'" -%}
{% if posts_for_locale.size > 0 %}
<div class="post-list">
  {% for post in posts_for_locale %}
  <article class="post-card">
    <p class="post-meta">
      {% if post.category %}<span class="post-category post-category-{{ post.category }}">{{ post.category }}</span>{% endif %}
      <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%-d %b %Y" }}</time>
    </p>
    <h3 class="post-card-title">
      <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
    </h3>
    {% if post.excerpt %}
    <p class="post-card-excerpt">{{ post.excerpt | strip_html | strip }}</p>
    {% endif %}
    <a class="post-card-readmore" href="{{ post.url | relative_url }}">Read more →</a>
  </article>
  {% endfor %}
</div>
{% else %}
<p>No posts yet — check back soon.</p>
{% endif %}
