# Terceira event-source discovery

Companion to [the scan runbook](runbook-social-scan.md). Last researched: **2026-09-04, Atlantic/Azores**. This was a public-source discovery and quality pass, not an exhaustive signed-in Instagram/Facebook scan. A source is useful when it supplies new, verifiable local events or corrects existing details, not simply when its homepage loads.

## Search procedure

1. Load existing events, recurring schedules, open PRs, and the last scan's access gaps. Search the complete event file; its final date is not a coverage watermark.
2. Check official calendars first, then organizer programmes, then discovery services. Paginate until the requested date range is covered or record where access stops. Retain ongoing exhibitions and verified later announcements.
3. Use the query matrix below to look beyond the existing account inventory. Pair place names with the current year and each month in the next 90 days. Portuguese month names usually find more local announcements; repeat in English for visitor-facing and science sources. Date-search filters find recently indexed pages, not necessarily upcoming events.
4. Follow the organizer, venue, co-author, and collaborators from each useful result. Read the original detail page or flyer. Record the source's role before promoting it to the runbook/resources pages.
5. Measure useful yield: new events, corrections, duplicates, held leads, and access gaps. A duplicate with a corrected distance or registration deadline still improves the data.

### Query matrix

Replace `{year}` and `{month}` at scan time; do not keep a hard-coded previous year. Use quotes around place names, not an unqualified `Terceira` which also matches the Portuguese word for "third". Start broad, then narrow by domain/account discovered in results.

| Coverage | Example searches | Follow-up |
|---|---|---|
| Island-wide | `"Ilha Terceira" eventos {month} {year}`; `"Terceira Island" events {year}` | Confirm physical event location, not just a mention of the island. |
| Both municipalities | `"Angra do Heroísmo" agenda {month} {year}`; `"Praia da Vitória" eventos {month} {year}` | Search each municipality separately; use linked calendars and pagination. |
| Parish/community | `"Serreta" festas programa {year}`; `"Porto Martins" atividades {month} {year}`; `"Biscoitos" filarmónica {year}` | Rotate parish names from both municipalities; follow juntas, Casas do Povo, philharmonics, and festival committees. Confirm the parish is on Terceira. |
| Sport/walking | `"Ilha Terceira" (trail OR caminhada OR corrida) {year}` | Follow the organizer, programme, rules, and registration provider; distinguish start times from bus transfers. |
| Nature/volunteering | `"Terceira" (bioblitz OR biodiversidade OR "limpeza costeira") {year}` | Follow project partners and local environmental groups; check registration requirements. |
| Science/workshops | `"Angra do Heroísmo" (oficina OR workshop OR simpósio) {year}`; `"Praia da Vitória" workshop {year}` | Confirm public access, eligibility, deadline, and actual venue. A headquarters footer is not an event location. |
| Family/literature | `"Ilha Terceira" (crianças OR famílias OR "apresentação de livro") {month} {year}` | Check libraries, bookshops, museums, schools, and associations; distinguish public events from school-only sessions. |
| Music/nightlife | `"Angra do Heroísmo" (concerto OR DJ OR karaoke) {month} {year}`; `"Praia da Vitória" concerto {year}` | Follow artist/promoter/venue posts, then compare weekly schedules and one-off guests. |
| Social-source discovery | `site:instagram.com "Ilha Terceira" eventos {year}`; `site:facebook.com "Praia da Vitória" programa {year}` | Search results are leads, not a substitute for opening posts and reading dates/slides. Record login gaps. |

On engines without Boolean support, split alternatives into separate searches. If results are sparse, try unaccented names and individual parish/venue names. A low-yield query is not evidence that no events exist.

## Newly useful sources and recovered routes

These recommendations are based on observed pages, not just plausible source names.

| Source / exact route | Role and access checked | Observed yield | How to use it |
|---|---|---|---|
| [AIR Centre events](https://www.aircentre.org/pt/events) | Primary organizer/co-organizer; calendar loaded in Chrome, detail pages readable publicly | New [BioBlitz Terceira](https://www.aircentre.org/pt/events/bioblitz-terceira-2026), 20 September 2026, Porto Martins; added to the data | Check the detail page's venue and registration status. The calendar also includes international/online events. |
| [Azores Bravos Trail](https://azoresbravostrail.com/) and [programme](https://azoresbravostrail.com/231-2/) | Primary organizer, Associação de Atletismo da Ilha Terceira; public pages readable | Corrects the existing 3 October 2026 listing's 65 km distance to 50 km and supplies start locations and registration deadline | Prefer the current programme over tourism summaries. Old URL slugs can survive a distance change; read the current body. |
| [byAçores Portuguese Terceira page](https://byacores.com/terceira/) | Secondary aggregator; Portuguese page checked in Chrome and web search | September/October 2026 parish festas and Bravos Trail leads; overlaps existing data | This route is useful despite the earlier stale English-route check. Follow original sources; duplicated or translated listings are not independent corroboration. |
| [Festing events](https://www.festingapp.com/en/events) | Secondary discovery; Chrome initial page and “View More Events” tested | Current Santa Bárbara, Hortênsia, CCCAH cinema, and Fórum Educativo listings | Use place search and pagination. [Hortênsia detail](https://www.festingapp.com/en/events/816bd228-23b6-40ad-ab6e-e30be7c6e611) links to CMAH, but its header ends 11 September while its programme says 10 September. Verify with the original; do not copy the header blindly. |

Add AIR Centre, Bravos Trail, and Festing to the public EN/PT resource lists. Keep byAçores as secondary and use the recovered Portuguese route. None of these observations proves complete coverage of the platform.

## Tested leads not promoted to a regular calendar

| Candidate | Finding on 2026-09-04 | Decision / next check |
|---|---|---|
| [AIR Centre marine-data workshop](https://www.aircentre.org/pt/events/workshop-enhancing-marine-biodiversity-data-collection-and-publication-2026) | 19–23 October on Terceira, but registration explicitly closed and attendance subject to selection | Do not advertise as open to new participants. No public drop-in session or precise venue was verified. |
| [Montanheiros Terceira news](https://www.montanheiros.com/category/terceira/) | Relevant first-party outdoor organization; no new future outing verified in this pass | Watch list. Follow the next dated activity announcement; do not manufacture a recurring walk. |
| [TERINOV](https://terinovazores.pt/) | Relevant institution, but homepage latest-news entries were from 2023 | Do not count homepage reachability as a current calendar. Find dated tenant/organizer announcements, such as AIR Centre. |
| [Festas & Arraiais Terceira](https://festasearraiais.pt/festas-este-mes/distrito/ilha-terceira) | September view exposed a Porto Martins lead already represented in the repo | Supplemental parish discovery, not a comprehensive island programme. |
| [Viral Agenda Terceira archive](https://www.viralagenda.com/pt/p/107378262618969) | Historical listings and misleading relative "Hoje" labels in retrieved content | Organizer discovery only until the absolute date/year is verified. |
| [CineEco extensions](https://cineeco.pt/extensoes-cineeco/) | Includes a 2026 Faial programme associated with Cine-Clube da Ilha Terceira | Organizer identity alone does not establish Terceira geography; do not import other-island events. |
| [Côrte-Real symposium lead](https://plataforma9.com/congressos/1-simposio-corte-real.htm) / [IHIT](https://www.ihit.pt/) | Secondary announcement for 13–15 October in Angra; IHIT site timed out in the web fetch | Hold pending organizer programme and actual venue. A contact address is not a confirmed venue. |

Additional source graph to investigate next: BioBlitz's named partners include Gê-Questa, Marine Waste on Terceira Island, and BioMUST4All/Universidade dos Açores. These are leads to locate through the organizer's links, not accounts claimed as scanned. Rotate parish committees and sports associations on subsequent passes rather than repeatedly searching only the existing bar list.

## Evidence and acceptance rules

- Separate publication date, event date, registration deadline, and scan date. Resolve relative words from the original post timestamp in `Atlantic/Azores`. Require a year or unambiguous original context.
- Use the event's actual location. Do not default a missing venue to Angra, and do not copy an organization's footer address into an event.
- Prefer current organizer programmes over older tourism descriptions. Keep the original URL even when an aggregator supplied the lead. Two mirrors of one feed are one source of evidence.
- A closed registration period does not cancel a public race already listed, but its description must say registration is closed. Do not imply a selected-attendee workshop is a public drop-in event.
- Preserve confirmed weekly programming when fresh posts are inaccessible. Removing a recurrence requires affirmative evidence, not absence of search results.
- Qualify a source by a clear first-party role or at least two dated local event examples. Record access and usefulness separately: an authoritative source can still be inaccessible or have no verified upcoming programme.
- Keep unresolved candidates in the scan report, not in published event data. Do not add unverified dates, venue addresses, admission prices, or recurring schedules.

## Coverage report template

For each actual scan, record:

```text
Checked at: YYYY-MM-DD HH:MM Atlantic/Azores
Publication window: ... (overlap the previous successful scan by at least 14 days)
Event window: today through +90 days; ongoing and later verified announcements included
Source URL / role / access method / observed date range:
Status: reachable | partial | blocked | empty-with-window | untested | stale
Evidence: example event/detail URL; exact access failure if any
Yield: new N / corrections N / duplicates N / held N
Next action: original organizer to verify, unread page range, or retry route
```

`empty-with-window` means the relevant calendar/filter actually loaded and showed no events in the stated range. A 403, login wall, parser returning zero, or an unread page is not an empty calendar. For automated sources also record fetched/parsed/local-candidate counts when available; a green workflow alone does not establish source health.

Suggested ingestion follow-up, not implemented here: replace guessed CMPV feeds and homepage-only discovery with verified live-agenda adapters, report partial/source failures separately from zero events, and test island filtering, multi-session dates, and exclusive iCal end dates. Keep automated touradas with their existing workflow.
