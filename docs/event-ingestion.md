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
python -m unittest discover -s scripts/tests -p 'test_*.py' -v
```

`--today YYYY-MM-DD` makes a reconciliation repeatable. The default date uses `Atlantic/Azores`. `--lookahead-days` sets the event window and `--max-events` caps writes; remaining candidates are counted as `deferred`. Ongoing events remain eligible until their inclusive end date.

The health report includes pages fetched, listings read, local records, parsed sessions, duplicates, candidates, deferred additions, exclusions, errors, and changed times needing review. The script leaves existing records intact; an observed correction is recorded in `corrections` for the manual scan. A healthy zero-addition run means the recognized source was read and reconciled. A source failure has status `degraded`, an error, and a failing process exit.

The `validate event ingesters` workflow exercises fixtures and failure paths without live network access. Live dry-runs verify current source availability separately.

## Shared parser contracts

`SourceHealth.fetch` reads a public page or data query and counts successful responses; `SourceError` identifies incomplete discovery. `run_ingester` calls a source's `discover_events(today, lookahead, health)` and validates the complete YAML output before writing. `published_dates` returns inclusive ranges or discrete session dates and rejects ambiguous mixtures; `published_time` reads clock labels while excluding duration and ticket-office lines. `parse_html` produces `HtmlNode` elements with attributes, children, class-token checks, document-order traversal, and visible text without executing scripts.
