# Official event ingestion

The Museu, CMPV, and What's On adapters use `ingest_health.run_ingester` for reconciliation, validated YAML writes, and source-health reporting. Their workflows attach `source-health.json` and publish the same counters in the Actions job summary. HTTP errors, unrecognized schemas, required detail failures, and incomplete pagination return exit status 1 before modifying event data.

| Source | Published input | Date and coverage rules |
|---|---|---|
| Museu de Angra | `/events/`, `/exhibition/temporarias/`, `/exhibition/mostras/`, archive pagination, and `.post-content` detail pages | Dated temporary exhibitions and exhibits; inclusive end dates; separate Sunday concerts and workshop sessions; admission tags require explicit evidence |
| CMPV | `index.php?op=agenda`, linked pagination, and agenda detail IDs | Listing dates verified against details; touradas belong to their dedicated adapter; venue and time come from the event body |
| What's On | Public Bondlayer website structure and the website's `repeater.bondlayer.com/fetch` read-only data query | Every advertised page; explicit Terceira island references; Portuguese displayed dates and venue names; discrete dates produce separate records |

What's On CMS timestamps can represent publication or administrative dates. The adapter uses the published date label for event dates and explicitly printed times for session times. An end-only exhibition needs a previously verified start in the canonical YAML. Recurring programmes are recorded as review warnings and belong in weekly data or dated session listings.

Museum HTTP requests can be blocked by the source's Cloudflare challenge even when the public pages are readable in Chrome. Such a run is degraded and fails with a health artifact. Use the browser for the manual audit and compare official tourism listings; an automated museum feed requires access permitted by the source operator.

## Commands

From the repository root:

```bash
python scripts/ingest_museu_angra.py --dry-run --health-report museum-health.json
python scripts/ingest_cmpv.py --dry-run --health-report cmpv-health.json
python scripts/ingest_whatson_azores.py --dry-run --health-report whatson-health.json
ruby scripts/validate_event_data.rb _data/special_events.yml
python -m unittest discover -s scripts/tests -p 'test_*.py' -v
```

`--today YYYY-MM-DD` makes a reconciliation repeatable. The default date uses `Atlantic/Azores`. `--lookahead-days` sets the event window and `--max-events` caps writes; remaining candidates are counted as `deferred`. Ongoing events remain eligible until their inclusive end date.

The health report includes pages fetched, listings read, local records, parsed sessions, duplicates, candidates, deferred additions, exclusions, errors, and changed times needing review. The script leaves existing records intact; an observed correction is recorded in `corrections` for the manual scan. A healthy zero-addition run means the recognized source was read and reconciled. A source failure has status `degraded`, an error, and a failing process exit.

The `validate event ingesters` workflow exercises fixtures and failure paths without live network access. Live dry-runs verify current source availability separately.

## Shared parser contracts

`SourceHealth.fetch` reads a public page or data query and counts successful responses; `SourceError` identifies incomplete discovery. `run_ingester` calls a source's `discover_events(today, lookahead, health)` and validates the complete YAML output before writing. `published_dates` returns inclusive ranges or discrete session dates and rejects ambiguous mixtures; `published_time` reads clock labels while excluding duration and ticket-office lines. `parse_html` produces `HtmlNode` elements with attributes, children, class-token checks, document-order traversal, and visible text without executing scripts.

## Translation

`scripts/ingest_translate.py` fills the other language of each ingested event's `name` and `description` (`_en` for Portuguese sources, `_pt` for Visit Azores) through an OpenAI-compatible chat-completions endpoint. It runs when the repository variables `TRANSLATION_API_URL` and `TRANSLATION_MODEL` and the secret `TRANSLATION_API_KEY` are all set and non-blank; otherwise it does nothing and raises no warning. `run_ingester(source, discover, language)` takes the source language; CMAH, Ticketline and Visit Azores call `translate_events` directly.

Scraped text is untrusted. Each event is sent in its own request, with a system prompt that tells the model to treat the strings as literal text. A reply is used only when it finishes normally and every translated value, with whitespace collapsed, has no control characters, markup or link absent from its source, and a length in proportion to its source. Otherwise the event stays untranslated, the warning appears in the source-health report and the job summary, and the locale gate stays red until a curator adds the fields. Warnings and logs never contain the key or URL credentials. `yaml_double_quote` escapes control characters, and the standalone ingesters parse the combined YAML before writing it.

## Duplicate matching

`run_ingester` skips a candidate that `_duplicate` (`scripts/ingest_health.py`) matches to a stored event, or to an earlier candidate of the same run, whose date range covers the candidate's day. A match is any of:

- the same `source_uid` or `source_url`;
- the same title and the same start time, whatever the venue string says. Titles are the same when case, accents, punctuation and a leading event-type label (`cinema`, `concerto`, `workshop`, ...) are ignored; two different labels are different titles. The start time is the first clock of the `time` field (`15:00–18:00` starts at 15:00). When the two venues are in different known localities (the record's `locality`, else an alias in `_data/venue_localities.yml`), the run fails with a `SourceError` naming both venues instead of choosing one;
- venue keys that agree (`_venue_key` gives variants of one place a single key: `S. Bento`, `Bar da Academia de Juventude e das Artes` and `(AJAIT)`, `Auditório do Ramo Grande, Praia da Vitória`) together with similar titles (`is_similar_match`), a shared title prefix, a stored title found in the candidate's description, or, at the same start time, titles where at least three content words of one (without stopwords, `com`/`with` and the event-type label) are all words of the other, optionally counting only the words after the first colon (`Mesa redonda: X` and `X: subtitle`).

The ingesters that use `matches_existing` (CMAH, Ticketline, Visit Azores, touradas) compare titles on the same date with `is_similar_match` alone. A stored record counts under each of its `name`, `name_en` and `name_pt` titles, in `_duplicate`, `same_instant` and `build_dedup_index`.

## Inclusive date ranges on the site

Upcoming, home, calendar, and archive selection compare `event.end_date | default: event.date` against today, so the inclusive end day stays upcoming and the next day moves to the archive. Cards and home previews label the complete period (`event_date_range.html`, silent for single-day events) and expose it to the client filter through `data-event-end-date`. Event JSON-LD carries the inclusive end date as date-only for multi-day ranges; timed single-day events keep the start time on both `startDate` and `endDate`. The client range filter keeps any event overlapping today through its exclusive horizon.

Both `date` and a present `end_date` must be unquoted ISO dates (YAML Date type) with `end_date` on or after `date`; `ruby scripts/validate_event_data.rb` rejects quoted or reversed ends before the site build.

## Listing kind and exhibition data

`kind` is optional and accepts `event` or `exhibition`; an omitted value means `event`. For an exhibition, `date` and the inclusive `end_date` are the display period, and `end_date` must be strictly after `date`. The record must carry the `exhibition` tag. Every multi-day record carrying that tag declares `kind` explicitly, including a dated programme that remains `kind: event`; single-day openings, talks, and guided tours may omit `kind`.

An opening reception, artist talk, or guided tour is a separate dated `kind: event` record naming the exhibition. Keep the longer display period on its own `kind: exhibition` record. An exhibition's `time` value is legacy data and is not an attendance time. `visiting_hours` and `visiting_hours_pt` are optional free-text schedules; provide them together in EN/PT only for a source-stated schedule, preserve every date restriction, and omit both when hours are unavailable. Translate the published schedule faithfully without adding hours. Older readers ignore these optional fields and continue reading existing event fields.

## Persistent event identity

Each published record has one unique opaque `id`. New IDs are UUIDs assigned by
`ruby scripts/assign_event_ids.rb`; existing IDs accept letters, numbers,
underscores, and hyphens. Keep the persisted ID when editing event metadata. New
occurrences receive new IDs. Installed consumers can ignore this additive field.

Run the assignment script after adding records and before validation. It preserves
existing IDs and all other parsed metadata, supports block and flow mappings, and
validates the complete output before writing. The publication gate is
`ruby scripts/validate_event_data.rb _data/special_events.yml`; missing, duplicate,
and malformed IDs fail with named errors. Assignment and validator tests run in
the event-data workflow, including manual-curation changes.

When merging duplicate records, retain the older persisted ID (check Git history),
reconcile metadata into that record, and record both IDs and the retained ID in the
PR body. Never reuse an event ID for a different occurrence. This schema does not
define aliases or redirects for IDs from merged records.

Optional `locality` is normalized curator metadata: `angra`, `praia`, or `other`.
Unknown records omit it. Consumers can ignore this additive field. Venue lookup,
geographic coverage, filter semantics, routes, and artwork policies have their own
consumer/curation changes.

## Website details and discovery

Website details consume persisted IDs. The canonical share
URL is `https://eventosterceira.pt/events/?id=<id>`; Portuguese uses
`/pt/events/?id=<id>`. Unknown IDs show an unavailable state.

Date shortcuts use Atlantic/Azores calendar days. Today and Tomorrow each contain
one day. This weekend contains Saturday and Sunday, or the remaining Sunday.
Next 7/31/365 days include today and exclude the following horizon. Exhibitions
match by overlap with their published viewing periods. Search ignores case and
accents. Every selected tag must match; date, kind, locality, search, and tags
combine with AND. The exact locality registry and curation policy are in
[locality-metadata.md](locality-metadata.md); unknown geography stays unknown.

Details read optional `price`, `price_en`, and `price_pt` as published price text;
a verified `free` tag identifies free admission. Missing scalar price or time
points readers to the complete programme and organizer. It does not assert that
the description contains no published price or schedule.

## Website artwork

The detail renderer reads `image`, localized `image_alt`, `image_credit`,
`image_rights`, and `image_source`. It displays uncropped posters and retains
textual event information when an image fails. Curators use organizer artwork only
with documented permission or a reusable license, follow approved hosting and
image-host validation, and record provenance/credit. A public social-media post
alone does not establish reuse permission. Permission-cleared acquisition samples
and native rendering coverage require their own verification.

The [artwork curation and fixture guide](artwork-fixtures.md) records permission, provenance, approved repository hosting, consumer failure checks and the original CC0 test-only delivery sample. Test fixtures remain outside the production dataset.
