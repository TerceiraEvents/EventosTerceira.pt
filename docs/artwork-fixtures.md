# Artwork curation and rendering checks

An organizer's public poster is not automatically permission to copy it. Record the license or written permission, source URL, copyright holder, required credit, allowed modifications and hosting route before adding artwork. If permission is unclear, retain the text-only event and leave artwork absent. Do not infer rights from Instagram visibility, bypass source access restrictions, or use a photograph of another event as its poster.

## Original permission-cleared rendering sample

The [shared fixture records](../scripts/tests/fixtures/artwork/events.yml) and equivalent [JSON](../scripts/tests/fixtures/artwork/events.json) are test-only data, outside `_data/special_events.yml`. Their original geometric PNG images are labelled TEST ONLY, contain no organizer content and have a [CC0-1.0 dedication](../scripts/tests/fixtures/artwork/LICENSE.txt). The generator and PNG metadata identify Codex desktop app (version unknown), model `gpt-6.1-sol`, local session ID `01a12d38-f796-77a1-b056-47c1eb6a90d5` as the producing agent. They test delivery and rendering, not real-event imagery coverage.

The [fetch/hosting manifest](../scripts/tests/fixtures/artwork/manifest.json) records actual public source URLs, image/png responses, SHA-256, dimensions, byte sizes and repository asset paths. The sample path is self-owned feature-branch source → existing `rehost_image._fetch` MIME/byte-limit checks → checksum verification → `/assets/images/test-fixtures/` repository asset → shared fixture → actual website detail renderer. This is the approved repository hosting route, not a release-asset upload. The `event-images` release lookup returned HTTP404 during this check; no release or tag was created. A release-hosting claim requires a separate successful run with authorized existing hosting.

`python3 scripts/generate_artwork_fixtures.py` invokes `main()` to regenerate the original portrait (600×900), landscape (900×600), and oversized (4096×3072) source PNG images and [generated manifest](../scripts/tests/fixtures/artwork/generated-manifest.json). It does not download an organizer image or overwrite the separately recorded fetch manifest. Missing, malformed URL, unavailable file and deliberately corrupt encoded PNG cases provide distinct failure inputs. The corrupt file is the first64 bytes of the original CC0 portrait, with an incomplete chunk and no complete image data. It is not a poster. TEST ONLY records must never be copied into the production event dataset.

## Shared data and hosting policy

Use `image` for a stable permitted image URL or repository path; `image_alt_en`/`image_alt_pt` describe the useful visual information without duplicating the entire event description. `image_credit`, `image_rights` and `image_source` identify provenance. Record proof of permission outside public data if it contains private contact details; publish the applicable rights statement and source. Retain canonical event IDs, dates, prices and descriptions independently of artwork.

Approved repository assets use `/assets/images/` and require a reviewable feature branch. The release rehost script accepts recognized JPEG/PNG/WebP/GIF MIME responses and refuses payloads over 10 MiB or HTML. The host validator rejects known unstable social image/page hosts; it is not a comprehensive URL-safety, file-decoding or rights validator. Consumers reject non-HTTP(S) links; native repository image paths use the documented simple filename path. Malformed and missing images must never remove an otherwise valid event. Report acquisition/validation failures and retain a truthful text-first listing instead of silently discarding it. Source metadata alone does not establish rights.

## Consumer expectations

Feed comparison remains name → attendance date/time → venue → published admission and works without an image. Artwork belongs to details with contain sizing, a complete-image link and useful accessibility description. Website details remove a failed image and retain the event and sharing controls. Native failure handling and provenance changes require their own reviewed app implementation and platform runs; JavaScript component tests alone are insufficient. Website full-size artwork has a separate labelled 44 px action with `noopener noreferrer`, independently of the provenance source link. Native details use a fixed image frame. Website images use responsive width and automatic height, so detail layout can move while an image decodes. Feed cards do not depend on images. Full-size opening exposes all poster text.

| Case | Automated check | Actual rendering requirement |
| --- | --- | --- |
| Missing | No image control; event and save remain | Confirm text-first layout in website/Android/iOS |
| Portrait / landscape | PNG dimensions/CRC/pixels, checksums, localized alt/provenance in actual website renderer | Decode native files, record intrinsic dimensions and all four edge markers; inspect full-size opening |
| Oversized | 4096×3072 PNG decoded by stdlib zlib with complete rows and CRC | Record native decoding/performance; no inferred memory guarantee |
| Malformed URL | No unsafe image/link control | Confirm failure feedback does not hide event/actions |
| Corrupt encoded PNG | Truncated original fixture, missing complete chunks; renderer error retains event/actions | Exercise actual browser and native decoder failures separately from URI rejection |
| Unavailable file | Trigger actual website renderer's image-error listener; retain exact event and actions | Exercise real HTTP404 in browser/native and record feedback |

Run `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_artwork_fixtures.py`, `node --test scripts/tests/test_detail_render.js`, `ruby scripts/validate_event_data.rb scripts/tests/fixtures/artwork/events.yml`, and `python3 scripts/validate_image_hosts.py scripts/tests/fixtures/artwork/events.yml`. The PNG tests decode bytes and verify complete border pixels; they do not claim Android/iOS decoding. Review locale copy, alt text, permission scope, host stability, accessible failure feedback, large text, full-size readability and image geometry before accepting a sample.

## Coverage and verification boundary

Measured shared data at the explicit 13 October 2026 calendar-day cutoff contains 650 records, 29 historical image fields, 134 active/upcoming records, and zero active/upcoming image fields. No production record has `image_rights`, `image_credit` or `image_source`. These fixtures leave production coverage at 0/134; a few original test images do not establish organizer artwork coverage. Existing historical images need a provenance audit before being described as permission-cleared. Actual browser/native observations belong in the task's proof outputs with platform, code revision and device settings; missing journeys remain unchecked.
