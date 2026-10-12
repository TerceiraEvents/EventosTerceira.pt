# Discovery UI

The website and app use green and cream, dark green primary text, and restrained
borders. Website semantic tokens live in `assets/css/style.css`; native equivalents
live in the app theme. Token changes require a side-by-side review of home,
navigation, cards, and details in EN/PT. Green-dark `#1a3a2a`, cream `#f7f9f4`, text
`#1a2e1a`, muted text `#557555`, borders `#c8dcc8`, radius 12 px, spacing 12 px.

Titles identify the event; attendance dates/time, venue, and published price follow.
Descriptions, complete addresses, source, map, booking, reporting, and sharing live
in details. Event cards work without artwork. Controls have a 44 px minimum target,
visible keyboard focus, text labels, and meaningful selected/expanded states.
Content wraps at enlarged text sizes. Reduced motion disables animated transitions.

## Website data states

The static website contains its dataset at publication. Event details do not fetch
another dataset. Publication time is labelled as a site build time, not organizer
verification. A filter with no matches offers reset/all dates. No published events
provides weekly browsing. Missing IDs show unavailable, ended records show ended,
and absent prices/times remain unknown. My Plans stores IDs and fallback titles in
this browser only; it does not create a notification. Storage failure is announced
and session changes remain usable. The website does not promise offline availability.

## Accessibility verification checklist

Automated: Azores midnight/DST/device timezone date predicates; exact-ID uniqueness
and preservation; combined facets; navigation and locale visibility; semantic controls.
Manual required: EN/PT 390 px and desktop reflow, 200/400% zoom, keyboard navigation,
visible wrapping navigation, details, saved removal, suggestion dialog, image failures, VoiceOver.
Native VoiceOver/TalkBack and enlarged system text require real platform runs.
A component test does not establish WCAG conformance.

Measured website token contrast against cream `#f7f9f4`: primary text 13.67:1,
muted text 4.88:1, dark green 11.77:1 (sRGB relative-luminance calculation).
These measurements cover those token pairs, not every inherited badge or image.

Open verification/content items: curator locality coverage; permission-cleared
artwork sample; canonical per-event social metadata (the static detail shell has
page-level metadata); mobile screen-reader and zoom audits; offline website use.
No native Android/iOS device is covered by the website tests.

Locality controls list only localities present in curated metadata and remain absent
when that metadata is unavailable. The live page filter delegates its full
predicate to `EventDiscovery.matches`; page-level tests cover facet conjunction,
accented search, locality, date/type URL round trips, locale links, and reset.
Detail DOM tests execute the actual renderer for EN/PT fields and share URLs.
Invalid saved data has an explicit clear/recovery action and remains intact until
that action is chosen. Storage denial has separate feedback.

Details and My Plans embed the full published dataset, including ended records.
The uncompressed detail HTML measured 532,260 bytes on 12 October 2026. This allows exact ended-event details without another request;
per-event generated documents are a possible future payload improvement. A map
action requires `map_url`; source and booking actions also require published URLs.

Primary navigation displays every destination in normal document flow in both languages. Links wrap into rows at narrow widths, retain at least 44 px targets, and keep the language switch visible.
