# AGENTS.md — EventosTerceira.pt (Jekyll website)

This is the Terceira Events community website: a Jekyll site served from
`main` via GitHub Pages. Judge every change by task completion — finding
today's events, finding weekly events, understanding an event, acting on
it. Compare against the existing UI first. Preserve or revert changes that
add taps, hide content or actions, truncate summaries, weaken contrast, or
introduce jargon without a demonstrated benefit.

## Stack and checks

- The declared CI environment is Ruby 3.3 (`ruby/setup-ruby` with
  `bundler-cache: true` in `.github/workflows/validate-templates.yml` and
  `validate-deployed.yml`; dependencies in `Gemfile` / `github-pages`).
  Run checks with that environment. Do not commit dependency changes solely
  to accommodate a local interpreter.
- Loudest test first: `bundle exec jekyll build --trace` plus
  `bundle exec ruby scripts/tests/test_built_site.rb`.
- Fast suites: `node --test scripts/tests/test_discovery.js
  scripts/tests/test_detail_render.js scripts/tests/test_event_filter.js`;
  token consistency `node scripts/check_discovery_tokens.mjs <native-theme>`
  and `node --test scripts/tests/test_discovery_tokens.mjs`.
- Data suites: `scripts/tests/test_event_identity.rb`,
  `test_event_localities.rb`, `test_tag_vocabulary.rb`,
  `test_special_event_duplicates.rb`, `test_post_lang.rb`,
  `test_event_ranges.rb`, `test_postal_address.rb`.

## Product contract

- Primary navigation is exactly seven links — Home, Weekly, Events,
  Venues, Blog, Contribute, Resources (`_layouts/default.html`, PT labels
  Início, Semanal, Eventos, Locais, Blogue, Contribuir, Recursos). The bar
  scrolls horizontally (`overflow-x: auto` in `assets/css/style.css`) and
  keeps the language control and narrow-width keyboard access usable. Never
  add Today, Saved, or Get the app to the navbar, and never hide
  destinations behind a new hierarchy.
- Home (`index.md`, `_includes/home_discovery.html`) leads with date
  shortcuts (Today / Tomorrow / This weekend), then upcoming event
  previews, then weekly and exhibition links, then the blog preview. The
  Get-the-app section (`#get-the-app`) stays separate from event discovery.
- The Events page (`special.md`) lists Events and Exhibitions as plain
  listing types through the kind selector in
  `_includes/event_search_bar.html`. Filters stay compact: Tags holds Free,
  Family, and topics; More filters holds locality plus its coverage note
  (events without a confirmed locality are included under All places). No
  large combination instructions, no standalone checkbox blocks.
- Filter behavior is AND across tags, locality, kind, range, and search
  (`matches` in `assets/js/discovery.js`, inline filter script in
  `_layouts/default.html`): truthful live result counts, an empty state,
  Reset visible only when a filter is active, state shared and restored
  through the URL and the locale link, Escape closing open filter menus and
  returning focus to the summary.
- Cards (`_includes/special_event_card.html`) show full published summaries
  with direct actions: Open in Maps, source (Published source / Instagram),
  Suggest an edit. Titles open the exact detail page (`/events/?id=` via
  `_includes/event_page.html` and `assets/js/event-details.js`). Summary
  language order is requested language, then the bare field, then the other
  published language, with known `lang` metadata on the summary element.
  Never invent translations; never suppress a published language.
- Detail Back reads “Back to results” / “Voltar aos resultados”: it steps
  through history when the referrer is same-origin, otherwise falls back to
  `/special/?range=all`.
- The browser has no Saved workflow. Event discovery uses the compact
  filters described above; never add a Saved workflow.

## Data and curator corrections

- `_data/special_events.yml` holds dated events, `_data/weekly.yml`
  recurring schedules, `_data/venues.yml` bilingual venue copy,
  `_data/event_tags.yml` the tag vocabulary, `_data/venue_localities.yml`
  venue-to-locality mapping.
- Curator corrections are authoritative within their stated scope: apply
  them to every duplicated copy (shared weekly data, bilingual venue
  fields; the bundled app copy lives in the app repository) without
  inventing another weekday. Never remove historical one-off dated events
  to satisfy a correction about recurring schedules. Distinguish a user
  correction from fresh organizer-source verification.

## Verification boundaries

- Platform associations live in `.well-known/assetlinks.json` and
  `.well-known/apple-app-site-association`; `_config.yml` includes that
  directory. `scripts/tests/test_associations.rb` checks the verified
  publisher, route contract and built output. `test_live_site.rb` checks
  direct association responses; ordinary page redirects have separate rules.
  Measure every declared host without following redirects, report MIME
  types, and check Apple's CDN before claiming iOS OS acceptance.
- Verify public signing identifiers in the exact app's existing developer
  session when available: the Apple App ID prefix and Play app-signing
  certificate differ from upload/debug identities. Keep private keys out of
  the workflow. Native declarations, the Apple portal capability, refreshed
  provisioning profiles, hosted files and release-signed OS delivery are
  separate checks; valid JSON or a simulator custom-scheme pass proves only
  its own stage.
- Color and token checks: `docs/discovery-tokens.json` must match
  `assets/css/style.css` exactly, and
  `scripts/tests/test_discovery_tokens.mjs` is a bounded source regression
  over the known venue-button selector set (coverage, specificity order,
  and contrast values). It is not a general browser CSS-cascade engine and
  does not prove every focus or focus-visible state. Real rendered normal,
  visited, hover, and focus labels and colors still need browser
  verification, alongside destinations and keyboard focus.
- Zoom claims require actual browser zoom: 400% zoom changes effective CSS
  pixels and device-pixel ratio, which a narrow viewport alone does not
  reproduce. Restore 100% afterwards. Chrome automatic translation can
  rewrite labels and `html lang`; verify against the original Portuguese and
  the rendered source without changing persistent user preferences.
- Test clocks and cached fixtures share one deterministic island day.
  Keep assertions as written; never silence failures or loosen expectations
  to obtain green tests.
- Screen-reader speech claims require real assistive-technology runs
  with the observed utterances recorded. Source inspection and focus logs
  alone do not establish speech. Generated captions can establish the
  focused utterance strings and activation actually observed, but not audio
  pronunciation; automatic announcements still need an actual
  assistive-technology run.
- Keep task tooling and data isolated, restore settings to baseline, and
  delete only exact disposable QA records. New dependencies require a stated
  license and reason; this repository stays on Jekyll.
