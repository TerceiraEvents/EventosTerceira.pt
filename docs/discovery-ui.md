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
and absent prices/times remain unknown. The website does not promise offline availability.

## Accessibility verification checklist

Automated: Azores midnight/DST/device timezone date predicates; exact-ID uniqueness
and preservation; combined facets; navigation and locale visibility; semantic controls.
Manual required: EN/PT 390 px and desktop reflow, 200/400% zoom, keyboard navigation,
visible wrapping navigation, details, suggestion dialog, image failures, VoiceOver.
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

Details embed the full published dataset, including ended records.
The uncompressed detail HTML measured 535,876 bytes on 12 October 2026. This allows exact ended-event details without another request;
per-event generated documents are a possible future payload improvement. A map
action requires `map_url`; source and booking actions also require published URLs.

## Component inventory and synchronization

The machine-readable [color inventory](discovery-tokens.json) records every color custom property in the website CSS and each native theme color. Hardcoded component color literals are outside this check; reviewing their contrast requires component measurements. The palettes share green/cream intent while retaining distinct values: website dark green `#1a3a2a`, cream `#f7f9f4`, body `#1a2e1a`, muted `#557555`; native primary `#2d5016`, background `#faf8f0`, body `#2c2c2c`, muted/inactive `#666666`, card white. Native primary dark is `#1a3009`; it is not the website dark green token. Website display headings use Playfair Display and body uses Source Sans 3 with system fallbacks. Native typography uses the platform font with 12/14/16/18/22/28-point roles and system scaling.

| Component | Website | Native | Required state and sizing |
| --- | --- | --- | --- |
| Discovery heading/card | Name, attendance range/time, venue, published admission | Same field order; detail title spans card width | Long EN/PT text wraps; unknown time/admission remains explicit |
| Detail actions | Share and reporting buttons; source, booking, map and full-artwork links | Touchable actions; Save/reminder expose accessible selected/disabled state | At least 44 px/points; state is expressed with text/semantics as well as color |
| Search/input/select | Native HTML controls, visible global focus ring | Platform input/picker and text labels | Keyboard/system-text support; label remains associated with control |
| Facet/type selector | Checkboxes/selects with preserved query state | Selected facet uses border-colored background and accessibility state | Selected, reset and unavailable choices remain distinguishable |
| Navigation | Wrapping links and visible language control | Five tabs, two scalable label lines and safe-area space | Active location, every destination reachable; route and large-text checks remain platform-specific |
| Feedback | Status/error paragraph and available action | Polite status/result announcement and Retry | Loading, no matches, absent data and failure use distinct language |
| Poster | Contain sizing, full-size link, failure paragraph | Contain sizing and full-size link | Alt/provenance and failure policy require cross-platform checks; permission-cleared sample remains open |

Pressed feedback follows the browser/platform control. Website keyboard focus is a 3 px `--focus` outline with 3 px offset. Native touchables use their platform pressed feedback; there is no claim that every native control supplies a desktop keyboard focus treatment. Disabled actions retain an accessible disabled state and an explanation; native Saved/reminder read failure must not become a false unselected state. Loading feedback must not prevent usable cached content being read. Website reduced-motion overrides animations, transitions and smooth scrolling. Native navigation animations and reduced-motion behavior need an actual system-setting audit.

Run `node scripts/check_discovery_tokens.mjs` to check website token drift and the six declared body/action contrast pairs. Run `node scripts/check_discovery_tokens.mjs /absolute/path/to/TerceiraEventsApp/src/utils/theme.js` to check both source palettes. The optional source is deliberately explicit: CI checks website source and the documented native pairs, and does not fetch another repository at runtime. Run `node --test scripts/tests/test_discovery_tokens.mjs` to exercise drift and insufficient-contrast failures. The checker exports `contrast(foreground, background)` for six-digit sRGB WCAG ratios and `checkTokens(manifest, css, nativeTheme)` for inventory equality and minimum-contrast validation; the optional native source must be supplied explicitly. This is a synchronization check, not a visual regression or whole-product contrast audit. Token changes update the inventory and require side-by-side EN/PT home/navigation/card/detail screenshots, 320/390 px and desktop, plus Android/iOS enlarged-text checks. The checklist records the devices actually run.

## State and copy inventory

[Data-state inventory](discovery-states.md) specifies the actual EN/PT feedback, recovery actions, timestamp meaning and unsupported states. It distinguishes the static website publication from native fetch/cache behavior. No new runtime dependency is needed for tokens or state documentation.
Primary navigation displays event discovery destinations in normal document flow in both languages. Contribute and Get the app are footer links. Links wrap into rows at narrow widths, retain at least 44 px targets, and keep the language switch visible.
