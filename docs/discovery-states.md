# Discovery data states

The website embeds published data in generated HTML; its build time measures publication, not organizer confirmation or continuous live verification. Native successful fetch time is an ISO device timestamp for a completed request, not the event's verification time. Persistent native cache has unknown fetch time. No stale-age cutoff or stale-specific copy is implemented: cached means a failed request retained usable data, without promising freshness. ISO values include their timezone marker; discovery date windows use Atlantic/Azores calendar days independently of device timezone.

| State | Website feedback and action | Native EN / PT feedback and action |
| --- | --- | --- |
| Initial loading | Static event content is present at publication; no simulated live-fetch loader | “Loading events” / “A carregar eventos”; wait for request; slow-fetch behavior needs actual device checks |
| Usable current data | Render embedded records and site build time | “Device fetched data at” / “Dados obtidos pelo dispositivo em” plus request timestamp; refresh available |
| Failed refresh with usable cache | No live-refresh state; reload requests the published document | “Using cached data. The network request failed.” / “A usar dados guardados. O pedido de rede falhou.”; Retry retains records |
| Old or age-unknown cache | Website publication time is not an organizer-verification age | No distinct stale state; cache fetch time is unknown and absent; Retry checks network |
| Failed request without usable data | Malformed embedded JSON: “Event data is unavailable. Reload this page to try again.” / “Dados indisponíveis. Recarrega a página para tentar novamente.” | “Events could not be loaded.” / “Não foi possível carregar eventos.”; Retry |
| Some malformed records | Static ingestion validation reports invalid records before publication | “Some published records cannot be displayed (%{count}). Available events remain listed.” / “Alguns registos publicados não podem ser apresentados (%{count}). Os eventos disponíveis continuam listados.”; retain valid records |
| No events for home dates | “No published upcoming events. Browse weekly regulars.” / “Sem eventos publicados. Consulta os eventos semanais.”; weekly browsing | “No published events for these dates. Browse upcoming events below.” / “Não há eventos publicados para estas datas. Consulte os próximos eventos abaixo.”; broader events |
| Filters have no matches | Zero result count; reset/all-dates controls | Zero result count; Reset filters / Limpar filtros; no fabricated event |
| Loaded dataset has no requested ID | “Event unavailable” / “Evento indisponível”; Browse events / Explorar eventos | “This event is unavailable in the current dataset. Any displayed information is a saved snapshot.” / “Este evento não está disponível nos dados atuais. A informação apresentada é uma cópia guardada.”; snapshot when present, otherwise unavailable |
| Cache does not contain requested ID | No promise of offline website detail | “This event is not in the available cache. Retry when connected to check the published record.” / “Este evento não consta dos dados guardados disponíveis. Tente novamente com ligação para consultar a publicação.”; Retry, retain snapshot |
| Ended record | Explicit ended status; published details remain accessible | “This event has ended.” / “Este evento terminou.”; retain record |
| Empty Saved/My Plans | Empty-state guidance; browse events | “No saved events yet. Save an event from its details.” / “Ainda não há eventos guardados. Guarde um evento nos detalhes.” |
| Browser storage unavailable | “Browser storage is unavailable. Changes last only while this page is open.” / “O armazenamento está indisponível. As alterações duram apenas enquanto esta página está aberta.”; session changes remain usable | Not applicable; device-storage failures have Retry feedback |
| Browser Saved data unreadable | Existing stored bytes remain intact until explicit Clear recovery; EN/PT warning and recovery button | Not applicable; storage read failure remains unknown |
| Native Saved read/write failure | Not applicable | “Could not read or save your events. Please try again.” / “Não foi possível ler ou guardar os eventos. Tente novamente.”; detail Saved state unknown disables changes until Retry succeeds |
| Reminder state unknown | Website does not promise native reminders | “Reminder state could not be read. Your event and saved events remain available.” / “Não foi possível ler o estado do lembrete. O evento e os eventos continuam disponíveis.”; Retry, independent calendar/Saved information remains available |

Website storage feedback uses `role=status`; filters announce counts without announcing each card. Native counts, cache/error and partial-record messages use polite live regions. Native accessibility announcements still require VoiceOver/TalkBack checks. Button states use accessible selected/disabled properties. Enlarged text must wrap feedback and keep Retry/removal reachable; website zoom and native scaling remain separate verification journeys. The color inventory checks normal-size text against a 4.5:1 minimum for its declared pairs; large text may use 3:1, and focus/non-text controls require 3:1 against their adjacent background. These thresholds are requirements for the manual audit, not coverage claims for every control.

Saving is browser/device local and does not request notification permission or create a reminder. Dataset refresh reconciles saved IDs with published records; missing records retain explicitly identified snapshots. These semantics do not imply cross-device sync or offline website availability.

## Verification matrix

| Scenario | Automated evidence | Actual runtime evidence and remaining work |
| --- | --- | --- |
| Partial/all-invalid refresh | Native production fetch regression preserves valid records; static ingestion validation | Native failure injection pending |
| Identity correction/missing snapshot | Native Saved/identity/detail tests; website actual renderer tests | Website and task-local Pixel 8 API35 emulator exact-link/save/restart checked; parent agent reports equivalent standalone iOS26.5 simulator checks at app main `8c2c96c` in `outputs/ios-runtime-repair-proof.json` |
| Detail Saved/reminder read rejection | Production native JSX/data-loading tests | Native storage-failure and reminder permission journeys pending |
| Combined filters/no matches | Website production predicate and native date/facet tests | Website 320 px and task-local Pixel 8 API35 emulator EN/PT combined-filter/Back checks; parent agent reports standalone iOS26.5 simulator facets/exact-detail/Back checks; full keyboard/AT pending |
| Slow fetch, disk cache, reconnect | Complete production timing/reconnect matrix pending | Actual slow/offline/error runs on both native platforms pending |
| Enlarged text | Native production layout tests and measured task-local Pixel 8 API35 emulator 200% before/after captures | iOS enlarged text, Android TalkBack, physical-device iOS VoiceOver and website 400% zoom pending |

A passed JavaScript export validates bundles, not native accessibility, calendar permissions, notification behavior or offline operation. Use the task's criterion-level acceptance checklist to record later measurements rather than treating this inventory as conformance.

The iOS simulator observations in this inventory are parent-agent reported evidence from Codex desktop app, model `gpt-6.1-sol`, local session ID `01a12d38-f796-77a1-b056-47c1eb6a90d5`; they were not independently run by the documentation author. The simulator checks do not establish physical-device VoiceOver coverage.
