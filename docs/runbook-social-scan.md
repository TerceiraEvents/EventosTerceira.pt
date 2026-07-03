# Runbook: Manual Social-Media Event Scan

> **Purpose:** Step-by-step guide for kicking off a manual Instagram/Facebook scan to find new events and write them into `_data/special_events.yml` via a PR.
> **Cadence:** Run once a week (or whenever you notice the upcoming-events list is getting thin).
> **Time required:** ~30–60 minutes depending on how active venues have been.

---

## Context

Several event sources post to Instagram and Facebook but are not covered by the automated ingest workflows (which handle CMAH iCal, Ticketline, Museu Angra, CMPV, Visit Azores, and Whatson Azores). The manual scan fills the gap for:

- Venue-specific nightlife events (Havanna Club, Porta 42, Tasca do Camões, The Texan / Garden Club)
- Bookshop/cultural events (Lar Doce Livro)
- City-council Instagram posts that pre-announce events before they appear in the iCal feed

The canonical list of venue social handles lives in `_data/venues.yml`. The canonical list of other resources is at `eventosterceira.pt/resources/`.

---

## Prerequisites

- You are logged into **Instagram** in the browser (the account that follows all the venue accounts).
- You are logged into **Facebook** in the same browser session.
- You have a GitHub account with write access to this repo (or can open a PR from a fork).
- Today's date is noted — you will need it to distinguish upcoming vs already-past events.

---

## Step 1 — Check what's already in the file

Before scanning, open `_data/special_events.yml` and note the most recent `date:` entries so you know what's already covered.

Quick way: https://github.com/TerceiraEvents/EventosTerceira.pt/blob/main/_data/special_events.yml

Scroll to the bottom. The file is sorted roughly chronologically. Note the latest date present so you don't duplicate.

Also check the **live site** for the current upcoming-events list: https://eventosterceira.pt/

---

## Step 2 — Check open issues for an existing scan

Before starting, look at https://github.com/TerceiraEvents/EventosTerceira.pt/issues to see if there is already an open issue titled "New events to add: [date range]". If one exists covering recent dates, read it to see what was already found and whether a PR was opened for it. Start your scan from the day after the last covered date.

---

## Step 3 — Scan the CMAH official events page (fastest, most complete)

This single page aggregates all municipally-supported events and is the most efficient place to start:

**URL:** https://www.angradoheroismo.pt/eventos

Also check the Museu de Angra do Heroísmo events calendar — it often has upcoming cultural events not yet on the CMAH page:

**URL:** https://museu-angra.cultura.azores.gov.pt/events/

**Facebook:** https://www.facebook.com/MuseuDeAngraDoHeroismo/ (11K followers — often posts events same-day)

**Instagram:** @museu.angra (2.5K followers)

Scroll through the full list. For each upcoming event **not already in `special_events.yml`**, note:
- Event name (PT and EN if bilingual)
- Date(s) and time(s)
- Venue name
- Any ticket/price information visible

This page typically yields the most events per minute of effort. Priority targets here:
- **Teatro Angrense** performances
- **CCCAH (Centro Cultural e de Congressos)** concerts and shows (the "Angra Convida" series in particular)
- **Casa do Sal** and **Museu de Angra do Heroísmo** cultural events
- **Biblioteca Pública** events
- **Cinefreguesias** outdoor cinema series (recurring summer programme)

> Note: Some of these are auto-ingested via `ingest_cmah.py` (runs daily via `ingest-cmah.yml`). Cross-check before adding — if an event is already in the file, skip it.

---

## Step 4 — Scan Instagram accounts

Navigate to each account below and scroll the grid looking for event flyers (posts with dates, times, venue names). Click each flyer post to read the caption for full details. Focus on posts from the last 7–10 days, and note the relative timestamp ("X hours ago", "X days ago") to estimate the post date.

### Priority accounts (most likely to have new events)

| Account | Platform | What to look for |
|---|---|---|
| `@angradoheroismo` | Instagram | CMAH-sponsored concerts, exhibitions, festival announcements |
| `@livraria_lardocelivro` | Instagram | Weekly agenda carousel, concert/workshop/poetry posts |
| `@havannaangra` | Instagram | Weekend DJ/live-act schedule posts (Fri/Sat/Sun) |
| `@porta_42` | Instagram | Saturday night DJ/theme nights |
| `@tascadocamoes` | Instagram + Facebook | Live music acts (check both — Facebook often has more detail) |
| `@thegardenclub.angra` | Instagram | Periodic special nights (less frequent) |
| `@thetexanbar` | Instagram | Check "Eventos" story highlight; grid posts rare |

### Secondary accounts (check if time permits)

| Account | Platform | Notes |
|---|---|---|
| `@winenot.terceira` | Instagram | Occasional live music nights |
| `@sala.319` | Instagram | Primarily daily lunch menus; skip unless something unusual |
| `@fullrange_rave` | Instagram | Page was unavailable as of May 2026 — check if it's back |
| `@amit.academiamusical` | Instagram | Active (254 followers); formerly @auditorioamit which is dead |
| `@museu.angra` | Instagram | Museu de Angra do Heroísmo — events, exhibitions, cultural programming (2.5K followers) |
| `@twinstheclub` | Instagram | Major Angra nightclub — recurring Fri/Sat nights; check for special one-off events |

### For each event post found

1. Read the full caption (scroll within the post modal if needed).
2. Note: name, date, time, venue, any ticket/price info, and the post URL.
3. Check whether it's a **recurring weekly event** (already in `_data/weekly.yml`) or a **one-off special event** (goes in `_data/special_events.yml`).
4. Skip anything already in the file.

### Tips for reading Instagram posts efficiently

- The **weekly agenda carousel** from `@livraria_lardocelivro` is a single multi-slide post published on Mondays — swipe through all slides to get the full week's schedule in one go.
- Havanna Club often posts a single reel listing **3 nights at once** (Fri/Sat/Sun) — one post, three events.
- Posts from the `@angradoheroismo` account are almost always upcoming (they rarely post recaps without a date header).
- If a post says "Amanhã" (Tomorrow) or "Este sábado" (This Saturday), use today's date to calculate the absolute date.

---

## Step 5 — Scan Facebook pages

Some venues post events primarily or exclusively on Facebook. Check these pages:

| Page | What to look for |
|---|---|
| **Tasca do Camões** (`facebook.com/tascadocamoes`) | Live music acts — the Photos tab often shows flyers most clearly |
| **Ilha Terceira - Eventos** (community group) | Community-shared events from sources not otherwise covered |
| **Agenda Cultural Praia da Vitória** (Facebook page) | Events in Praia da Vitória specifically |
| **Museu de Angra do Heroísmo** (facebook.com/MuseuDeAngraDoHeroismo/) | Facebook + Instagram (@museu.angra) | Museum events, exhibitions, and cultural programming — 11K FB followers, very active |
| **Twins The Club** (facebook.com/twinsclubazores/) | Facebook + Instagram (@twinstheclub) | Major nightclub; posts weekly DJ/event schedule — mostly recurring Fri/Sat nights |

> Note: Havanna Terceira and Teatro Angrense Facebook pages were inaccessible as of May 2026. Try searching for them by name if the direct URL fails.

For Facebook, the **Photos** tab of a page is often the fastest way to spot event flyers. Click a flyer photo to open it and read the post caption.

---

## Step 6 — Deduplicate against `special_events.yml`

Before writing anything up, do a quick browser search (Ctrl+F) on the raw file for key words from each event you found (venue name, partial event name, or date string like `2026-06-06`) to confirm it isn't already there.

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

Scanned Instagram and Facebook sources from `venues.yml` on **[TODAY'S DATE]**.
The following events were found that are not yet in `_data/special_events.yml`.

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

| Account | Platform | Status |
|---|---|---|
| @angradoheroismo | Instagram | ✅ Active — N new events found |
| ... | | |
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
  instagram: https://www.instagram.com/p/...  # source post URL (use 'facebook:' key for FB sources)
  tags:
  - live-music              # see _data/event_tags.yml for valid tags — canonical only
  - free
```

### Valid tags — canonical only

These are the only valid tag slugs (source of truth: [`_data/event_tags.yml`](../_data/event_tags.yml)). **Anything outside this list is silently dropped from URL filtering on the calendar page** — it doesn't fail CI, it just doesn't filter.

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

Insert new entries **in chronological order by `date:`**. The file has section comments like `# May 2026` — add your entries under the appropriate month heading, or create a new heading if needed.

### Addresses for common venues

| Venue | Address |
|---|---|
| Lar Doce Livro | Rua de São João 22-24, 9700-184 Angra do Heroísmo |
| Tasca do Camões | Rua Da Rocha 64, 9700-169 Angra do Heroísmo |
| Havanna Club | Av. Infante D. Henrique, 9700-098 Angra do Heroísmo |
| Teatro Angrense | Rua da Rosa, 9700-155 Angra do Heroísmo |
| CCCAH | Rua Conselheiro Dr. José Pereira, 9700-040 Angra do Heroísmo |
| Casa do Sal | Rua da Rosa 11, 9700-155 Angra do Heroísmo |
| Museu de Angra do Heroísmo | Ladeira de São Francisco, 9701 Angra do Heroísmo |
| Centro Interpretativo | Rua da Rosa, Angra do Heroísmo |
| Biblioteca Pública | Rua da Biblioteca, Angra do Heroísmo |
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

If there are open auto-submission PRs touching `_data/special_events.yml`, decide whether to merge those first (cleaner history) or pull their changes into your branch (avoids a later conflict).

---

## Step 8d — Pre-flight: validate tags against the canonical list

CI does not currently fail on non-canonical tags — they just silently don't filter. Before opening the PR, sanity-check from the repo root:

```bash
# extract every tag your branch added, dedupe
git diff main..HEAD -- _data/special_events.yml | awk '/^\+  - / && !/^\+  - [a-z]+:/ {print $2}' | sort -u

# compare against the canonical slug list
yq '.[].slug' _data/event_tags.yml | sort -u
```

Every entry in the first list must also appear in the second. If not, fix it before opening the PR (map per the table in Step 8) or the tag won't filter.

---

## Step 9 — Open a PR

Once you've added your entries to the YAML, open a pull request:

- **Title:** `Add [N] new events: [brief description] (#ISSUE_NUMBER)`
- **Body:** Reference the tracking issue with `Closes #NNN` or `See #NNN`
- **Branch:** Create from `main`, name it something like `events/may-22-scan`

The CI will run `validate-events.yml` automatically. If it passes, merge directly to `main` (no review required for data-only PRs).

After merging, the `daily-rebuild.yml` workflow will rebuild and deploy the site within ~5 minutes.

---

## Step 10 — Close the tracking issue

Once the PR is merged, close the tracking issue (or it closes automatically if you used `Closes #NNN` in the PR body).

---

## What NOT to add

- **Recurring weekly events** (karaoke nights, Noche Latina, DJ resident nights) → these belong in `_data/weekly.yml`, not `special_events.yml`. Check `weekly.yml` before adding.
- **Events that have already passed** by the time you're writing the PR.
- **Events with no confirmed date** (e.g. "coming soon" posts with no date).
- **Events already auto-ingested** by the daily workflows (CMAH iCal, Ticketline, Museu Angra, CMPV, Visit Azores, Whatson Azores, **Touradas à corda**). Double-check before adding manually — the touradas calendar in particular has 5–10 entries per week during the May–September season, all auto-added.

---

## Automated ingest coverage (what you do NOT need to scan manually)

These sources are covered by daily GitHub Actions workflows and do not need manual scanning:

| Source | Workflow file | Script |
|---|---|---|
| CMAH iCal feed | `ingest-cmah.yml` | `scripts/ingest_cmah.py` |
| Ticketline (Angra + Praia) | `ingest-ticketline.yml` | `scripts/ingest_ticketline.py` |
| Museu de Angra do Heroísmo | `ingest-museu-angra.yml` | `scripts/ingest_museu_angra.py` |
| Câmara Municipal Praia da Vitória | `ingest-cmpv.yml` | `scripts/ingest_cmpv.py` |
| Visit Azores | `ingest-visit-azores.yml` | `scripts/ingest_visit_azores.py` |
| Whatson Azores (government) | `ingest-whatson-azores.yml` | `scripts/ingest_whatson_azores.py` |
| Touradas à corda | `ingest-touradas.yml` | `scripts/ingest_touradas.py` |

If an automated workflow is producing errors or missing events, check the **Actions** tab: https://github.com/TerceiraEvents/EventosTerceira.pt/actions

---

## Kicking off with an AI assistant

This whole workflow can be handed off to Claude (or another AI with browser access) with a single prompt:

> "Scan Instagram and Facebook using my account to update events from the venues and resources listed at https://eventosterceira.pt/resources/ and give me the information to make a PR that adds new events. Only use tags from this canonical set — anything else gets silently dropped from the calendar filter: `kid-friendly, live-music, cinema, theater, dance, nightlife, karaoke, food-drink, exhibition, literature, workshop, free, outdoor, bullfighting`. Map common look-alikes: concert→live-music, theatre→theater, comedy→theater, film→cinema, talk→literature, sports→outdoor, art (static)→exhibition, art (hands-on)→workshop. Skip touradas à corda — already auto-ingested. For any flyer image you want to display, point me at the source URL and I will re-host it (don't embed raw Instagram/Facebook URLs as `image:`, they rot)."

The AI will:
1. Load the resources page to get the account list
2. Navigate to each Instagram/Facebook account
3. Read recent posts and extract event details
4. Cross-check against `special_events.yml` to avoid duplicates
5. Return formatted YAML ready to paste into a PR, plus a draft tracking issue
6. Flag any image URLs that need to go through the rehost workflow

After the AI returns the findings, you review, open the issue (or ask the AI to open it), apply the YAML to the file, and open the PR.

**Prompt for just the issue:**
> "Write an internal GitHub issue detailing all the new events found, following the format of issue #141."

**Prompt for the PR YAML only:**
> "Format all new events as YAML entries for `_data/special_events.yml` using the schema in that file. Use only canonical tags from `_data/event_tags.yml` (kid-friendly, live-music, cinema, theater, dance, nightlife, karaoke, food-drink, exhibition, literature, workshop, free, outdoor, bullfighting)."
