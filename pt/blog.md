---
layout: default
title: Blogue - Eventos da Terceira
description: Notícias, guias e histórias sobre a vida na Terceira — desde reaberturas de espaços a sítios de comida favoritos e dicas para quem chega à ilha.
permalink: /pt/blog/
lang: pt
lang_alt: /blog/
---

<h2>Blogue</h2>

<p class="section-intro">Notícias, guias e histórias sobre a vida na Terceira — desde reaberturas de espaços a sítios de comida favoritos e dicas para quem chega à ilha.</p>

<p class="section-intro" style="font-size: 0.9em; opacity: 0.85;"><em>Os artigos do blogue só estão disponíveis em inglês de momento. Estamos a trabalhar em traduções &mdash; se quiseres ajudar, vê a página <a href="{{ '/pt/contribute/' | relative_url }}">Contribuir</a>.</em></p>

{% if site.posts.size > 0 %}
<div class="post-list">
  {% for post in site.posts %}
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
