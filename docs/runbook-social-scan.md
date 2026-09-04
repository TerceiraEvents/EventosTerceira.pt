# Runbook: Manual Social-Media Event Scan

> **Purpose:** Find and verify Terceira events across official calendars, organizer websites, search, Instagram, and Facebook, then update the data through a PR.
> **Cadence:** Run once a week (or whenever you notice the upcoming-events list is getting thin).
> **Time required:** ~30–60 minutes depending on how active venues have been.
> **Source status last verified:** 2026-09-04.

---

## Context

Several event sources are not fully covered by the automated ingest workflows. The manual scan has three jobs:

1. Check that the official automated sources are not lagging behind the live public agendas.
2. Fill the gap for event flyers that only appear on social accounts.
3. Discover organizers outside the existing culture/nightlife list, especially parish, sport, nature, science, and community activities.

This covers both Angra do Heroísmo and Praia da Vitória. The manual scan is especially useful for:

- Venue-specific nightlife events (Havanna Club, Porta 42, Tasca do Camões, The Texan / Garden Club)
- Bookshop/cultural events (Lar Doce Livro)
- City-council Instagram/Facebook posts that pre-announce events before they appear in the feeds
- Praia cultural events shared through Agenda Praia Cultural or the municipal Facebook page

The canonical list of venue social handles lives in `_data/venues.yml`. The canonical list of other resources is at `eventosterceira.pt/resources/`.

Use the [source-discovery playbook and dated audit](event-source-discovery.md) for reusable queries, newly tested sources, and unresolved leads. This runbook describes the procedure, not proof that every source was reached in a particular run.

## Source Inventory

Use this as a maintained starting list for Angra and Praia scans. It is not a guarantee of comprehensive social coverage: private groups, stories, login walls, bot protection, and short-lived posts can all hide events. Record any inaccessible source in the scan report instead of silently treating it as checked.

| Source | Area | Role and current scan action |
|---|---|---|
| CMAH events (`angradoheroismo.pt/eventos`) | Angra | Primary first-party calendar. Compare the page and iCal with the repo. The iCal is live, but imported descriptions and all-day times still need manual verification. |
| `@angradoheroismo` | Angra | Primary municipal social account. Scan recent posts and every slide in carousels. |
| Teatro Angrense / CCCAH | Angra | Use CMAH and the venue/ticket seller as primary evidence. Do not rely on unofficial or empty Facebook profiles. |
| Museu de Angra do Heroísmo + `@museu.angra` | Angra | The website endpoints returned 403 on 2026-09-04. Treat Instagram and the CMAH calendar as the practical primary sources until the feed recovers. |
| BPARLSR (`bparlsr.azores.gov.pt/destaques/`) | Angra | First-party library calendar and monthly BiblioAgenda. The site is Cloudflare-protected, so scan it in a browser and use its calendar/iCal export when available. |
| Casa do Sal / Oficina d'Angra (`@oficinadangra`) | Angra | Primary source for Casa do Sal. The old direct Casa do Sal Facebook page remains unavailable. |
| Lar Doce Livro (`@livraria_lardocelivro`) | Angra | Scan every slide of the pinned monthly agenda carousel and individual corrections. Do not infer a weekly recurrence from one month's dated programme. |
| AMIT (`@amit.academiamusical`, `@espacoamit`, `@cjazzamit`) | Angra | Check the academy, event-space, and jazz-course accounts. The former `@auditorioamit` handle is unavailable. |
| AAIP (`@aaipazores`) | Angra | Independent arts source. Cross-check ticketed events on Shotgun when its search is accessible. |
| Tasca do Camões, Havanna, Porta 42, Texan, Garden Club, Twins, Wine Not?, Sala 319 | Angra/Praia nightlife | Scan recent grids, reels, and highlights. Revalidate `_data/weekly.yml` against current posts before treating a recurring night as already covered. |
| CMPV agenda (`cmpv.pt/index.php?op=agenda`), `@cmpraiadavitoria`, `@agendapraiacultural` | Praia | Primary municipal sources. The direct agenda and touradas category are available in the browser. Agenda Praia Cultural's newest visible grid post was from July 2026 on the 2026-09-04 check. |
| Auditório do Ramo Grande | Praia | Cross-check CMPV, Agenda Praia Cultural, and Ticketline. |
| Casa Museu Vitorino Nemésio / Biblioteca Municipal Silvestre Ribeiro | Praia | Check CMPV and Agenda Praia Cultural directly. |
| Cultura Açores (`culturacores.azores.gov.pt/agenda/`) | All islands | Current official culture agenda. The former `cultura.azores.gov.pt` address no longer resolves. The current site may require a browser because automated requests return 403. |
| What's On Azores | All islands | Official discovery source, but automated access returned 403 on 2026-09-04. Use the Portuguese browser agenda for canonical place names because the English translation can mangle Terceira locations. |
| byAçores Terceira agenda | Terceira | Discovery-only cross-check. The Portuguese `/terceira/` page showed September/October 2026 listings in a browser on 2026-09-04; the previously checked English route appeared stale. Check the exact route and year, then follow original sources. `agendacores.pt` redirects here. |
| AIR Centre (`aircentre.org/pt/events`) | Regional/international | Primary source for citizen science and marine activities. Inspect event location and registration eligibility; the Terceira headquarters address does not make every event local. |
| Azores Bravos Trail (`azoresbravostrail.com`) | Terceira | Primary organizer programme for races and walking. Check the current edition, actual start locations, and registration deadlines, not just a tourism summary. |
| Festing (`festingapp.com/en/events`) | Portugal/all islands | Secondary discovery source with current local listings. Use browser pagination and place search, then follow organizer links; do not treat all results as Terceira events. |
| Ticketline | Angra + Praia | Useful for paid shows. Multi-session event pages can be assigned the wrong city/date by the current parser, so verify the Terceira session manually before adding it. |
| Songkick + Bandsintown | Angra/Terceira | Secondary music discovery. Bandsintown exposed more current local listings than Songkick on 2026-09-04. Confirm the date and venue with the artist, promoter, or venue. |
| Eventbrite + Shotgun | Terceira | Discovery for organizer-posted workshops, festivals, and independent arts. Expect bot/rate limits and verify local venue details. |
| Visit Azores | All islands | The configured `/en/events` URL returned 404 on 2026-09-04. Do not count it as scanned until a replacement endpoint is found. |
| Touradas à corda | Terceira | Covered by `ingest-touradas.yml`. Do not transcribe manually unless the workflow is broken. |
| Ilha Terceira - Eventos Facebook group | Terceira | Community discovery only. Report explicitly when the group feed could not be scanned completely. |
| Cine-Clube da Ilha Terceira (`@cineclubedailhaterceira`) | Angra | First-party cinema source. Use its season announcement plus the CMAH season page; enter the actual dated screenings rather than a generic every-Sunday recurrence. |
| Sabores da Horta (`@sabores_dahort_a`) | Praia | First-party source for strawberry-picking hours and family activities. Recheck the profile because hours can be seasonal. |

Earlier checks on 2026-09-04 found `@fullrange_rave`, `@auditorioamit`, and the direct Casa do Sal Facebook page unavailable; Agenda da Terceira had not posted a current agenda since February 2026; Explore Terceira was a business directory rather than an event calendar; Songkick had substantially fewer current listings than Bandsintown; the old Cultura Açores domain failed DNS; and the configured Visit Azores endpoint returned 404. These are dated, route-specific observations, not permanent closures. The later browser check recovered a useful Portuguese byAçores route.

### Finding and qualifying new sources

Do not limit discovery to the static account list. During each scan:

1. Inspect co-authors, tagged accounts, venue tags, promoters, and recurring collaborators on confirmed local posts.
2. Search the next 90 days using the geographic/category query matrix in the [discovery playbook](event-source-discovery.md). Include ongoing events and verified announcements beyond that horizon, not just weekend nightlife.
3. Promote a candidate to the maintained list only when it has a clear first-party role or at least two recent, dated, Terceira-specific event posts.
4. Use aggregators to find leads. Prefer the organizer, venue, artist, municipality, or ticket page for the final event details.
5. Follow calendar pagination and detail pages. Try the site's linked Portuguese route or browser view when a cached/translated page is stale. Do not invent feed endpoints or call an inaccessible source empty.
6. Record the exact URL, access method, date checked, observed date range, useful leads, access failures, redirects, and parser errors in the PR body. Use the source-status template in the discovery playbook.

### Maintaining recurring-event data

Treat `_data/weekly.yml` as a current schedule, not a permanent catalogue:

1. Recheck each affected venue's most recent first-party post or profile before changing a weekly record.
2. Record the evidence URL where available and the date and scope of verification. A dated YAML comment can distinguish organizer evidence from a maintainer's local confirmation. Never make `verified_on` imply that an unconfirmed start time was rechecked.
3. Add a weekly event when the organizer states a recurring day, recent first-party history demonstrates a stable cadence, or a maintainer explicitly confirms the current recurrence. A single dated poster is not sufficient by itself.
4. Remove or pause a weekly listing only with affirmative evidence of cancellation, closure, an expired seasonal programme, or a maintainer's correction. Sparse posts, login failures, and unsuccessful searches do not demonstrate cancellation. Preserve the existing listing and report what remains uncertain. The 2026-09-04 maintainer confirmations of Camões Thursday Latin night and ongoing Texan karaoke must not be undone merely because a fresh flyer is unavailable.
5. Put monthly agendas, seasonal cinema programmes with skipped weeks, rotating concerts, and other specifically dated schedules in `_data/special_events.yml`.
6. Update the matching summary in `_data/venues.yml` whenever a weekly schedule changes so the venue and weekly pages do not contradict one another.

---

## Prerequisites

- You are logged into **Instagram** in the browser (the account that follows all the venue accounts).
- You are logged into **Facebook** in the same browser session.
- You have a GitHub account with write access to this repo (or can open a PR from a fork).
- Today's date is noted — you will need it to distinguish upcoming vs already-past events.

---

## Step 1 — Check what's already in the file

Before scanning, read all of `_data/special_events.yml`, including entries whose start date has passed but whose `end_date` is still upcoming. Also inspect `_data/weekly.yml` and its evidence notes.

Quick way: https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/special_events.yml

The file contains appended scan sections and is not globally chronological. The last entry or maximum date is not a coverage watermark. Search the whole file by date, distinctive title, venue, and `source_url`/`source_uid`; compare alternate-language titles too.

Also check the **live site** for the current upcoming-events list: https://eventosterceira.pt/

---

## Step 2 — Check open issues for an existing scan

Before starting, inspect open issues and PRs at https://github.com/TerceiraEvents/EventosTerceira.pt for overlapping scans and submission-worker entries. Read their findings and avoid duplicating pending additions.

Use an overlapping publication window: start at least 14 days before the last successful scan, or inspect at least the last 14 days of posts on a first pass. Also inspect pinned programmes, future-dated calendar pages, and corrections to existing upcoming events. Search events from today through the next 90 days, retaining any verified later announcements you find. Never start after the previous scan's event-date range: late announcements can concern dates that were already searched. Record publication and event windows separately.

---

## Step 3 — Scan official web agendas first

Start with official web agendas before social media. They are faster to scan and they prevent duplicate manual entries.

| Source | URL | What to check |
|---|---|---|
| CMAH official events | https://www.angradoheroismo.pt/eventos | Angra municipal events, Teatro Angrense, CCCAH, Casa do Sal, Museu, Biblioteca, Cinefreguesias |
| Praia da Vitória municipal events | https://www.cmpv.pt/index.php?op=agenda | Praia municipal events, Auditório do Ramo Grande, Biblioteca Municipal, Casa Museu Vitorino Nemésio, and the dedicated touradas category |
| What's On Azores | https://whatson.azores.gov.pt/agenda/ | Filter or scan for `Terceira`; use Portuguese place names and compare against the repo because the feed can lag or miss items |
| BPARLSR highlights | https://bparlsr.azores.gov.pt/destaques/ | First-party library calendar, BiblioAgenda, and calendar exports |
| Cultura Açores Agenda Cultural | https://culturacores.azores.gov.pt/agenda/ | Filter to `Terceira`; useful for cultural listings and public institutions |
| byAçores Terceira | https://byacores.com/terceira/ | Portuguese island page and its agenda links; verify absolute dates and original sources |
| AIR Centre | https://www.aircentre.org/pt/events | Citizen science and marine activities; check local venue and whether attendance/registration is open |
| Azores Bravos Trail | https://azoresbravostrail.com/ | Current organizer programme, walking/race start locations and registration status |
| Festing | https://www.festingapp.com/en/events | Browser-based secondary discovery; paginate and confirm actual event geography |
| Ticketline | https://ticketline.sapo.pt/ | Paid shows at Angra/Praia venues |
| Songkick / Bandsintown | https://www.bandsintown.com/c/angra-do-heroismo-portugal | Touring concerts; also check Songkick, then cross-check artist and venue sources |
| Eventbrite / Shotgun | https://www.eventbrite.pt/d/portugal--terceira/events/ | Organizer-posted workshops and independent ticketed events |

For each upcoming event **not already in `special_events.yml`**, note:

- Event name (PT and EN if bilingual)
- Date(s) and time(s)
- Venue name
- Any ticket/price information visible
- Source URL
- Publication date/year, whether registration is open, and any eligibility restrictions

Priority targets:

- **Teatro Angrense** performances
- **CCCAH (Centro Cultural e de Congressos)** concerts and shows (the "Angra Convida" series in particular)
- **Casa do Sal** and **Museu de Angra do Heroísmo** cultural events
- **Biblioteca Pública** events
- **Cinefreguesias** outdoor cinema series (recurring summer programme)
- **Auditório do Ramo Grande** shows in Praia
- **Casa Museu Vitorino Nemésio** and **Biblioteca Municipal Silvestre Ribeiro** events in Praia
- **Parish associations, sports organizers, and nature/science groups** from the discovery playbook; cover both municipalities, not only Angra's established venues

> Note: Many of these are auto-ingested by daily workflows. Cross-check before adding. If the live official agenda has an upcoming event that the repo does not, add it as a manual backfill and mention the source in the PR.

---

## Step 4 — Scan Instagram accounts

Navigate to each account below and scroll the grid looking for event flyers. Read captions, every carousel slide, pinned programmes, highlights, and later corrections. Use Step 2's overlapping publication window, and record the actual publication date where available rather than treating search-result freshness as the event date.

### Priority accounts (most likely to have new events)

| Account | Platform | What to look for |
|---|---|---|
| `@angradoheroismo` | Instagram | CMAH-sponsored concerts, exhibitions, festival announcements |
| `@museu.angra` | Instagram | Official Museu de Angra do Heroísmo account; exhibitions, family programs, outdoor museum events |
| `@amit.academiamusical` | Instagram | Academy concerts, showcases, auditions |
| `@espacoamit`, `@cjazzamit` | Instagram | AMIT event-space programme and jazz-course events |
| `@oficinadangra` | Instagram + Facebook | Primary Casa do Sal programme, workshops, concerts, and community projects |
| `@aaipazores` | Instagram | Independent arts events and Shotgun-ticketed programmes |
| `@livraria_lardocelivro` | Instagram | Pinned monthly agenda carousel, concert/workshop/poetry posts; scan every slide |
| `@havannaangra` | Instagram | Weekend DJ/live-act schedule posts (Fri/Sat/Sun) |
| `@porta_42` | Instagram | Saturday night DJ/theme nights |
| `@tascadocamoes` | Instagram + Facebook | Live music acts (check both — Facebook often has more detail) |
| `@thegardenclub.angra` | Instagram | Periodic special nights (less frequent) |
| `@thetexanbar` | Instagram | Check "Eventos" story highlight; grid posts rare |
| `@twinstheclub` | Instagram | Major nightclub; skip recurring weekly nights, add one-off guest DJ/special events |
| `@cineclubedailhaterceira` | Instagram | First-party season announcements and individual cinema screenings |
| `@sabores_dahort_a` | Instagram | Seasonal strawberry-picking schedule and family activities |

### Secondary accounts (check if time permits)

| Account | Platform | Notes |
|---|---|---|
| `@winenot.terceira` | Instagram | Occasional live music nights |
| `@sala.319` | Instagram | Primarily daily lunch menus; skip unless something unusual |
| `@caes.do.mar`, `@ruadireita.azores` | Instagram | Seasonal independent culture and festival programmes |
| `@cmpraiadavitoria`, `@agendapraiacultural` | Instagram | Praia municipal and cultural programmes; note stale posting periods |

### For each event post found

1. Read the full caption (scroll within the post modal if needed).
2. Note: name, date, time, venue, any ticket/price info, and the post URL.
3. Check whether it is a genuinely **recurring weekly event** or a **dated special event**. Revalidate any matching `_data/weekly.yml` record before relying on it.
4. Skip only an exact current duplicate. If the new source changes a day, time, status, or cadence, update the weekly data or add the dated event.

### Tips for reading Instagram posts efficiently

- The pinned **monthly agenda carousel** from `@livraria_lardocelivro` is a multi-slide post. Swipe through every slide and enter dated items individually unless the agenda explicitly demonstrates a weekly cadence.
- Havanna Club often posts a single reel listing **3 nights at once** (Fri/Sat/Sun) — one post, three events.
- Even official accounts publish recaps. Confirm the event year and full date before adding anything.
- Resolve "Amanhã" (tomorrow) or "Este sábado" (this Saturday) from the **post's publication date**, in `Atlantic/Azores`, not the date of the scan. A repost date may differ from the original. If the original timestamp/year is unavailable or contradictory, keep the item as an unresolved lead instead of guessing.

---

## Step 5 — Scan Facebook pages

Some venues post events primarily or exclusively on Facebook. Check these pages:

| Page | What to look for |
|---|---|
| **Tasca do Camões** (`facebook.com/tascadocamoes`) | Live music acts — the Photos tab often shows flyers most clearly |
| **Oficina d'Angra / Casa do Sal** (`facebook.com/oficinadangra`) | Casa do Sal cultural events and workshop flyers |
| **Lar Doce Livro** (`facebook.com/livrarialardocelivro`) | Book launches, poetry nights, weekly agenda cross-posts |
| **Havanna Terceira** (`facebook.com/p/Havanna-Terceira-100059128671983/`) | Weekend nightlife flyers when Instagram lacks detail |
| **Município Praia da Vitória** (`facebook.com/MunicipioPraiaVitoria`) | Praia municipal programs, exhibitions, family activities |
| **Agenda Praia Cultural** (`facebook.com/agendapraiacultural`) | Praia-specific cultural events and venue posts |
| **Ilha Terceira - Eventos** (community group) | Community-shared events from sources not otherwise covered |

> Note: The direct Casa do Sal page (`facebook.com/casadosal.angra`) and an apparent Teatro Angrense Facebook profile were still not useful on 2026-09-04. Use CMAH, Ticketline, `@oficinadangra`, and venue websites instead.

For Facebook, the **Photos** tab of a page is often the fastest way to spot event flyers. Click a flyer photo to open it and read the post caption.

---

## Step 6 — Deduplicate against `special_events.yml`

Search the complete file for each candidate's date, distinctive title, venue, and source identity. Account for Portuguese/English titles, date ranges, and alternative names. Compare detail fields, not just presence: a matching event may need its time, location, race distance, cancellation, or registration information corrected. Check open PRs as well. Run the duplicate validator in Step 8d after editing.

Raw file URL for fast Ctrl+F: https://raw.githubusercontent.com/TerceiraEvents/EventosTerceira.pt/main/_data/special_events.yml

---

## Step 7 — Open a tracking issue

Create a new GitHub issue titled:

```
New events to add: [START DATE]–[END DATE], [YEAR] (sourced from Instagram, Facebook & CMAH)
```

Use this template (matches the pattern of issues #141, #161):

```markdown
## Summary

Checked [actual sources and access methods] on **[DATE, TIMEZONE]**.
Publication lookback: [range]. Event horizon: [range, plus any later announcements].
List new events, corrections to existing entries, unresolved leads, and access gaps separately.

---

## Events to Add

### 1. [Event Name]
- **Date:** YYYY-MM-DD ([Day of week])
- **Time:** HH:MM
- **Venue:** [Venue name]
- **Address:** [Full address]
- **Description:** [English description]
- **Description PT:** [Portuguese description]
- **Source:** [URL] (@account)
- **Tags:** [comma-separated tags]

### 2. ...

---

## Already in the file (confirmed)

- [Event name] — [Date], [Venue] ✅

---

## Sources Scanned

| Source URL | Method | Observed date range | Status | New / corrected / duplicate / held |
|---|---|---|---|---|
| [Exact route or account] | [browser/feed/search] | [range] | [reachable/partial/blocked/empty-with-window/untested/stale] | [counts and evidence links] |
```

This issue serves as both a paper trail and a checklist. Check off each event as you add it to the YAML.

---

## Step 8 — Write the YAML entries

Each new special event goes as a new list item in `_data/special_events.yml`. The schema is:

```yaml
- date: YYYY-MM-DD          # required; use end_date: YYYY-MM-DD for multi-day events
  name: "Portuguese name"   # required
  name_en: "English name"   # add if different from Portuguese
  venue: Venue Name         # required; must match the name in venues.yml if the venue is listed there
  address: "Full address, postcode Angra do Heroísmo"
  map_url: https://www.google.com/maps/search/?api=1&query=...
  time: "HH:MM"             # 24-hour, quoted string
  description: "English description prose."
  description_pt: "Portuguese description prose."
  source_url: https://...   # original organizer/venue event detail, when available
  instagram: https://www.instagram.com/p/...  # source post URL (use 'facebook:' key for FB sources)
  tags:
  - live-music              # see _data/event_tags.yml for valid tags — canonical only
  - free
```

### Valid tags — canonical only

These are the only valid tag slugs (source of truth: [`_data/event_tags.yml`](../_data/event_tags.yml)). Unknown tags fail the tag-vocabulary CI check and do not work correctly with calendar filtering.

`kid-friendly` · `live-music` · `cinema` · `theater` · `dance` · `nightlife` · `karaoke` · `food-drink` · `exhibition` · `literature` · `workshop` · `free` · `outdoor` · `bullfighting`

Common mistakes (do **not** use; map to the canonical slug instead):

| Looks intuitive | Use this canonical slug |
|---|---|
| `concert` | `live-music` |
| `theatre` (UK spelling) | `theater` |
| `comedy` | `theater` |
| `film` | `cinema` |
| `talk` / `lecture` | `literature` |
| `sports` | `outdoor` |
| `art` (static) | `exhibition` |
| `art` (hands-on) | `workshop` |
| `festival` | (split between `live-music`, `theater`, `outdoor`, etc. — pick what actually describes it) |

### Ordering

Keep new entries chronological within their existing month or dated scan section. Do not reorder the entire file just to add an event; older scan sections are not globally sorted.

### Addresses for common venues

| Venue | Address |
|---|---|
| Lar Doce Livro | Rua de São João 22-24, 9700-182 Angra do Heroísmo |
| Tasca do Camões | Rua Da Rocha 64, 9700-169 Angra do Heroísmo |
| Havanna Club | Av. Infante D. Henrique, 9700-098 Angra do Heroísmo |
| Teatro Angrense | Rua da Esperança 48-52, 9700-073 Angra do Heroísmo |
| CCCAH | Rua Conselheiro Dr. José Pereira, 9700-040 Angra do Heroísmo |
| Casa do Sal | Estrada Gaspar Corte-Real, 9700-030 Angra do Heroísmo |
| Museu de Angra do Heroísmo | Ladeira de São Francisco, 9700-181 Angra do Heroísmo |
| Centro Interpretativo | Rua da Rosa, Angra do Heroísmo |
| Biblioteca Pública | Rua do Morrão 42, 9700-054 Angra do Heroísmo |
| Porta 42 | Rua de São João, Angra do Heroísmo |

---

## Step 8b — Re-host any images before linking them

If you want a flyer to render on the event card, you cannot reference the raw Instagram / Facebook / CDN URL directly — those image URLs rot within days (sometimes hours). The site repo has a re-hosting workflow that fetches the bytes once and stores them as a permanent GitHub release asset:

- Script: [`scripts/rehost_image.py`](../scripts/rehost_image.py)
- Workflow: [`.github/workflows/rehost-image.yml`](../.github/workflows/rehost-image.yml) (trigger via the **Actions** tab → *Rehost image* → *Run workflow*, paste the source URL + a slug)

The output is a `https://github.com/.../releases/download/...` URL. Use **that** as the `image:` field on the event entry. If you skip this step, the image will work for a few days and then 404 — and the daily-rebuild won't catch it.

> Background: the mobile-app submission worker does this automatically (it re-hosts before opening the PR). For manual scans you have to do it by hand or your flyers will silently die.

---

## Step 8c — Check the submission-worker PR queue before you write your PR

The mobile app's *Suggest* button and the website's `/suggest/` form both open PRs via [`event-submit-worker`](https://github.com/TerceiraEvents/event-submit-worker). Before you stack a manual scan PR on top of `main`, glance at:

https://github.com/TerceiraEvents/EventosTerceira.pt/pulls

If open auto-submission PRs touch `_data/special_events.yml`, inspect them and avoid overlapping additions. Note dependencies or likely conflicts in your PR. Do not merge another PR or incorporate its unrelated changes without authorization; the maintainer handles merging.

---

## Step 8d — Pre-flight: run the repository validators

Run the actual checks from the repo root before committing. These validate the complete event file, not just a fragile extraction of added diff lines:

```bash
bundle exec ruby scripts/tests/test_tag_vocabulary.rb
bundle exec ruby scripts/tests/test_special_event_duplicates.rb
python3 scripts/validate_image_hosts.py _data/special_events.yml
bundle exec jekyll build --trace
bundle exec ruby scripts/tests/test_built_site.rb
git diff --check
```

Use the repository's documented Ruby/Bundler environment. Record actual results and any local environment limitations; do not claim a build passed unless it ran. After publishing, inspect both `validate event data` and `validate templates and structured data` in GitHub Actions.

---

## Step 9 — Open a PR

Once you've added your entries to the YAML, open a pull request:

- **Title:** `Add [N] new events: [brief description] (#ISSUE_NUMBER)`
- **Body:** Reference the tracking issue with `Closes #NNN` or `See #NNN`
- **Branch:** Create from `main`, name it something like `events/may-22-scan`

Request review after the CI checks finish. The repository maintainer decides when to merge; this runbook must not merge its own PR into `main`.

After merging, the `daily-rebuild.yml` workflow will rebuild and deploy the site within ~5 minutes.

---

## Step 10 — Close the tracking issue

Once the PR is merged, close the tracking issue (or it closes automatically if you used `Closes #NNN` in the PR body).

---

## What NOT to add

- **Recurring weekly events** (karaoke nights, Noche Latina, DJ resident nights) → these belong in `_data/weekly.yml`, not `special_events.yml`. Check `weekly.yml` before adding.
- **Events that have already passed** by the time you're writing the PR.
- **Events with no confirmed date** (e.g. "coming soon" posts with no date).
- **Events already represented** in the repo, whether manually entered or auto-ingested. A configured workflow is not proof that its current source is healthy. Use the status table below and backfill missing events from verified sources.

---

## Automated ingest coverage (spot-check, but do not duplicate)

These sources have configured daily GitHub Actions workflows. Configuration or a green run does not prove successful coverage: some ingesters return successfully after fetching no usable events. Spot-check the live source against `_data/special_events.yml`; backfill verified omissions with the original source URL.

| Source | Workflow file | Status verified 2026-09-04 |
|---|---|---|
| CMAH iCal feed | `ingest-cmah.yml` | Healthy enough to produce candidates; manually verify times, descriptions, and duplicates |
| Ticketline (Angra + Praia) | `ingest-ticketline.yml` | Reachable; multi-session pages can be assigned the wrong city/date |
| Museu de Angra do Heroísmo | `ingest-museu-angra.yml` | Website REST and iCal requests returned 403; use Instagram/CMAH |
| Câmara Municipal Praia da Vitória | `ingest-cmpv.yml` | Configured endpoint guesses returned 404; scan the live site/social accounts |
| Visit Azores | `ingest-visit-azores.yml` | Configured events URL returned 404 |
| Whatson Azores (government) | `ingest-whatson-azores.yml` | Automated request returned 403; browser/search/byAçores fallback required |
| Touradas à corda | `ingest-touradas.yml` | Keep as the canonical automated source and spot-check Actions |

If an automated workflow is producing errors or missing events, check the **Actions** tab: https://github.com/TerceiraEvents/EventosTerceira.pt/actions and mention the backfill in the PR body.

For source-health checks, distinguish fetch status, parsed event count, Terceira candidate count, duplicates, and missing verified events. Report a failed/blocked/non-calendar response as such, not as zero events. CMPV currently tries guessed feed paths, while the What's On ingester inspects homepage JSON-LD; neither substitutes for paginating the live agenda. Do not assume an event is in Angra merely because its page mentions Terceira. Parser changes need their own tested implementation; this runbook does not repair those ingesters.

---

## Kicking off with an AI assistant

This whole workflow can be handed off to Claude (or another AI with browser access) with a single prompt:

> "Run `docs/runbook-social-scan.md` and its linked `docs/event-source-discovery.md` playbook. Check official calendars, organizer programmes, Instagram, Facebook, and discovery services. Use the geographic/category query matrix, overlapping publication window, ongoing events, and future announcements; do not stop at the existing venue list. Follow tagged organizers and collaborators to qualify new sources. Cross-check every candidate against all of `_data/special_events.yml`, `_data/weekly.yml`, and open PRs. Preserve maintainer-confirmed recurrences unless there is affirmative evidence of a change. Prefer first-party details, resolve relative dates from the original post timestamp, and report blocked/partial sources without claiming comprehensive coverage. Use canonical tags from `_data/event_tags.yml`. Skip touradas à corda unless its workflow is broken. Re-host any flyer before using it as `image:`. Create a feature branch from current main, add verified events and source-documentation changes, run repository validations, open a PR, and request review. Never merge the PR."

For an authorized implementation, the assistant follows this runbook and the linked discovery playbook, updates the data/docs on a fresh branch, validates locally, and opens the PR. It reports verified additions, corrections, source improvements, unresolved leads, and CI status. It does not merge. For a research-only request, return findings and suggested changes without publishing or changing the repository.

**Prompt for just the issue:**
> "Write an internal GitHub issue detailing all the new events found, following the format of issue #141."

**Prompt for the PR YAML only:**
> "Format all new events as YAML entries for `_data/special_events.yml` using the schema in that file. Use only canonical tags from `_data/event_tags.yml` (kid-friendly, live-music, cinema, theater, dance, nightlife, karaoke, food-drink, exhibition, literature, workshop, free, outdoor, bullfighting)."
