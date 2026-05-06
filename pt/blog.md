---
layout: default
title: Blogue
description: Notícias, guias e histórias sobre a vida na Terceira — desde reaberturas de espaços a sítios de comida favoritos e dicas para quem chega à ilha.
permalink: /pt/blog/
lang: pt
lang_alt: /blog/
---

<h2>Blogue</h2>

<p class="section-intro">Notícias, guias e histórias sobre a vida na Terceira — desde reaberturas de espaços a sítios de comida favoritos e dicas para quem chega à ilha.</p>

{%- comment -%}
  Filter to PT posts only — those with `lang: pt` and a
  `/pt/blog/...` permalink. Untranslated EN posts show up on
  `/blog/` instead of here.
{%- endcomment -%}
{%- assign posts_for_locale = site.posts | where: "lang", "pt" -%}
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
    <a class="post-card-readmore" href="{{ post.url | relative_url }}">Ler mais →</a>
  </article>
  {% endfor %}
</div>
{% else %}
<p>Ainda não há artigos &mdash; volta a passar por aqui em breve.</p>
{% endif %}
