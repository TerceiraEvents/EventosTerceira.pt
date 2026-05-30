---
layout: default
title: Contribute
description: How to contribute to Terceira Events. Suggest a venue, fix an event listing, or help build the project.
lang_alt: /pt/contribute/
---

<div class="homepage-intro">
  <h2 style="border:none; padding:0; margin-bottom:0.75rem;">Want to add your venue or event?</h2>
  <p class="intro-text">There's no criteria for inclusion &mdash; if you want on here, cool, we'll add you!</p>
</div>

<div class="homepage-buttons" style="max-width:580px;">
  <a href="{{ '/suggest/' | relative_url }}" class="homepage-btn btn-weekly">
    <span class="btn-icon">&#128221;</span>
    <span class="btn-title">Submit a Suggestion</span>
    <span class="btn-desc">Fill out the form and we'll review it</span>
  </a>
  <a href="#use-the-app" class="homepage-btn btn-special">
    <span class="btn-icon">&#128241;</span>
    <span class="btn-title">Use the App</span>
    <span class="btn-desc">Tap "Suggest Event" in the mobile app</span>
  </a>
  <a href="https://github.com/TerceiraEvents/EventosTerceira.pt" class="homepage-btn btn-venues" target="_blank" rel="noopener">
    <span class="btn-icon">&#128187;</span>
    <span class="btn-title">Open a PR</span>
    <span class="btn-desc">Submit changes on GitHub (if you're a nerd)</span>
  </a>
  <a href="https://www.instagram.com/chrisrackauckas/" class="homepage-btn btn-resources" target="_blank" rel="noopener">
    <span class="btn-icon">&#128242;</span>
    <span class="btn-title">Message Chris</span>
    <span class="btn-desc">Send a DM on Instagram @chrisrackauckas</span>
  </a>
</div>

<h2 id="use-the-app">Suggesting an Event from the App</h2>

<p class="section-intro">The easiest way to get an event on the site is to use the app. Grab it here:</p>

{% include app_store_badges.html %}

<div class="venue-card">
  <div class="venue-regulars">
    <ol>
      <li>Open the <strong>Terceira Events</strong> app on your phone (<a href="https://apps.apple.com/us/app/terceira-events/id6766769428">iOS</a> / <a href="https://play.google.com/store/apps/details?id=com.terceiraevents.app">Android</a>)</li>
      <li>From the Home screen, tap <strong>Suggest Event</strong></li>
      <li>Fill in the form &mdash; only the event name, date, and venue are required</li>
      <li>Optionally add time, address, Google Maps link, description, Instagram link, and your name (for credit)</li>
      <li>Tap <strong>Submit</strong></li>
    </ol>
    <p>Your suggestion goes straight into our review queue. Once we check it over, it shows up on the site and in the app automatically.</p>
  </div>
</div>

<h2>Opening a Pull Request</h2>

<p class="section-intro">If you're comfortable with GitHub, you can submit changes directly. This is the fastest path because you skip the review queue &mdash; your PR shows up immediately once merged.</p>

<div class="venue-card">
  <h3>For a Special Event</h3>
  <div class="venue-regulars">
    <p>Add an entry to <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/special_events.yml"><code>_data/special_events.yml</code></a>:</p>
<pre><code>- date: 2026-06-15
  name: "Concert at Teatro Angrense"
  venue: Teatro Angrense
  address: Rua da Esperan&ccedil;a 48-52, Angra do Hero&iacute;smo
  map_url: https://maps.app.goo.gl/...
  time: "21:30"
  description: "Live music with special guest."
  instagram: https://www.instagram.com/p/...
  tags:
    - live-music
    - kid-friendly
</code></pre>
    <p>Only <code>date</code>, <code>name</code>, and <code>venue</code> are required. The <code>date</code> field must be in YYYY-MM-DD format.</p>
    <p><code>address</code> is the human-readable street address shown on the card. <code>map_url</code> is an optional Google Maps share link (e.g. <code>maps.app.goo.gl/...</code>) that powers the &quot;Open in Maps&quot; button &mdash; use it when you want to pin a precise location. If <code>map_url</code> is omitted, the button falls back to a Google Maps search of the address.</p>
    <p>Add a <code>tags</code> list to help visitors filter the calendar. Available tags are defined in <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/event_tags.yml"><code>_data/event_tags.yml</code></a>: <code>kid-friendly</code>, <code>live-music</code>, <code>cinema</code>, <code>theater</code>, <code>dance</code>, <code>nightlife</code>, <code>karaoke</code>, <code>food-drink</code>, <code>exhibition</code>, <code>literature</code>, <code>workshop</code>, <code>free</code>, <code>outdoor</code>, <code>bullfighting</code>.</p>
  </div>
</div>

<div class="venue-card">
  <h3>For a Weekly Recurring Event</h3>
  <div class="venue-regulars">
    <p>Add an entry to <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/weekly.yml"><code>_data/weekly.yml</code></a> under the appropriate day:</p>
<pre><code>- day: Wednesday
  events:
    - name: Karaoke Night
      venue: Tasca do Cam&otilde;es
      time: "20:30"
      description: Weekly karaoke at Cam&otilde;es
      address: Rua Da Rocha 64, Angra do Hero&iacute;smo
</code></pre>
  </div>
</div>

<div class="venue-card">
  <h3>For a New Venue</h3>
  <div class="venue-regulars">
    <p>Edit <a href="https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/venues.md"><code>venues.md</code></a> and add a new <code>venue-card</code> block following the existing pattern. Include the address, a Google Maps search link, description, and any relevant social media links.</p>
  </div>
</div>

<h2>Reaching Out Directly</h2>

<p class="section-intro">Not a fan of forms or GitHub? That works too.</p>

<div class="venue-card">
  <div class="venue-regulars">
    <ul>
      <li><strong>Instagram DM</strong> &mdash; <a href="https://www.instagram.com/chrisrackauckas/">@chrisrackauckas</a></li>
      <li><strong>In person</strong> &mdash; find Chris at karaoke nights. You'll know which one.</li>
    </ul>
    <p>Send a flyer, a description, a rough date, whatever you have. We'll sort it out.</p>
  </div>
</div>

<h2>What We Accept</h2>

<div class="venue-card">
  <div class="venue-regulars">
    <p>Pretty much anything happening on Terceira: concerts, festivals, bullfights, karaoke nights, dance parties, book launches, theater, cinema screenings, exhibitions, workshops, sports events, and everything in between.</p>
    <p>Both Angra do Hero&iacute;smo and Praia da Vit&oacute;ria &mdash; and anywhere else on the island.</p>
    <p>Events in Portuguese and English are equally welcome. If you want to promote your venue's weekly events, we'll add those too.</p>
  </div>
</div>
