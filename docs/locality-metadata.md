# Event locality metadata

`angra` and `praia` denote the urban localities of Angra do Heroísmo and Praia da
Vitória. They do not classify every place inside the two municipalities. `other`
is a curator-confirmed locality elsewhere on Terceira; missing metadata is unknown.
A search for a locality matches only its explicit event field.

The shared `_data/venue_localities.yml` registry contains four urban venue
identities and five exact aliases. Each entry has location-evidence URLs. The
CCCAH and library location pages specify Canada Nova and Rua do Morrão in Angra.
The municipal Recreio event page identifies its Angra venue, consistent with the
existing street-address record. Regional tourism identifies the Ramo Grande
location in Santa Cruz; the municipality identifies that named auditorium in
Praia da Vitória. These location pages were read on 12 October 2026. This is a
location check, not new verification of event dates, schedules, or admission.

`ruby scripts/assign_event_localities.rb` fills absent locality fields using exact
venue aliases. Ingestion runs it before validation. It uses YAML AST positions, validates the complete output, and preserves IDs, source
metadata, comments, and existing curator fields. It does not examine titles,
addresses, postal prefixes, translations, partial venue names, or GPS. Unknown
aliases stay unknown. Add an alias only with evidence for that venue's physical
location; generic museum names can represent satellite sites and need separate
curation. Registry changes do not require client-side matching or another fetch.

When correcting a venue, explicitly correct or remove its `locality` as well.
An existing field is a curator choice and the mapper never overwrites it. Removing
it allows the verified alias lookup to fill the corrected venue's locality.

## Coverage

Snapshot for 12 October 2026 (inclusive end dates): 649 records, 136 active/upcoming.
The five approved aliases cover 99 records with metadata: 85 Angra and 14 Praia; 550 remain unknown.
Among active/upcoming records, 47 are Angra and 11 Praia; 78 remain unknown.
These counts demonstrate a curated subset, not complete geographic coverage.
The alias tests and data gate cover exact matches, unknown/ambiguous names, curator
corrections, idempotence, and identity/source preservation.

## Links

- https://angradoheroismo.pt/local/centro-cultural-e-de-congressos-de-angra-do-heroismo/ — municipal CCCAH location.
- https://bparlsr.azores.gov.pt/biblio/espacos/localizacao/ — regional library location.
- https://angradoheroismo.pt/evento/rua-de-sentido-unico/ — municipal Recreio venue evidence.
- https://turismo.azores.gov.pt/pin/auditorio-ramo-grande/ — regional tourism location of Ramo Grande.
- https://www.cmpv.pt/index.php?op=70 — municipal identity of the Praia auditorium.
