"""Reduced fixtures from the museum's event and exhibition archive templates."""
import datetime as dt
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
import ingest_museu_angra as museum
from ingest_health import SourceError, SourceHealth

ARCHIVE = b'''<h1>Eventos</h1><div class="card"><div class="card-body">
<h5 class="card-title"><a href="/events/domingos-com-musica-52/">Domingos com M\xc3\xbasica</a></h5>
<p class="small mt-auto">04.10.2026 - 25.10.2026</p></div></div>
<nav><a class="next page-numbers" href="/events/page/2/">Seguinte</a></nav>'''
DETAIL = '''<h1>Domingos com Música</h1><div class="post-content">
<div class="open-close">04.10.2026 - 25.10.2026</div>
<p>Com a missão de valorizar o património musical, concertos no órgão histórico.</p>
<p>MUSEU DE ANGRA DO HEROÍSMO. CORO ALTO DA IGREJA DE NOSSA SENHORA DA GUIA. 11H00. Acesso livre.</p></div>'''.encode()


class MuseumArchiveTests(unittest.TestCase):
    def test_actual_archive_schema_and_pagination(self):
        records, pages = museum.parse_archive(ARCHIVE, museum.ARCHIVES[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["date"], dt.date(2026, 10, 4))
        self.assertEqual(records[0]["end_date"], dt.date(2026, 10, 25))
        self.assertEqual(pages, [museum.BASE_URL + "/events/page/2/"])

    def test_sunday_programme_is_discrete_not_continuous(self):
        record = museum.parse_archive(ARCHIVE, museum.ARCHIVES[0])[0][0]
        events = museum.parse_detail(DETAIL, record)
        self.assertEqual([event["date"] for event in events], [dt.date(2026, 10, day) for day in (4, 11, 18, 25)])
        self.assertTrue(all("end_date" not in event for event in events))
        self.assertEqual(events[0]["time"], "11:00")
        self.assertEqual(events[0]["venue"], "Igreja de Nossa Senhora da Guia")
        self.assertEqual(events[0]["tags"], ["live-music", "free"])

    def test_two_felting_sessions_include_the_date_in_body(self):
        record = {"name": "OFICINA Feltragem com Agulha", "date": dt.date(2026, 10, 31),
                  "end_date": dt.date(2026, 10, 31), "source_url": museum.BASE_URL + "/events/feltragem/"}
        detail = '''<div class="post-content"><p>Oficina em duas sessões.</p>
        <p>MUSEU DE ANGRA DO HEROÍSMO. SERVIÇO EDUCATIVO. 14H00 – 18H00.
        Inscrição na primeira sessão implica a participação na segunda sessão, a 7 de novembro.</p></div>'''.encode()
        events = museum.parse_detail(detail, record)
        self.assertEqual([event["date"] for event in events], [dt.date(2026, 10, 31), dt.date(2026, 11, 7)])
        self.assertNotIn("free", events[0]["tags"])

    def test_ongoing_exhibition_has_inclusive_end_date(self):
        fixture = '''<h1>Exposições</h1><div class="card"><h5 class="card-title">
        <a href="/exhibitions/diapasao/">Diapasão com Caixa</a></h5>
        <p class="small">06.10.2026 - 01.11.2026</p></div>'''.encode()
        record = museum.parse_archive(fixture, museum.ARCHIVES[1])[0][0]
        detail = b'<div class="post-content"><p>MUSEU DE ANGRA DO HERO\xc3\x8dSMO. Instrumento de Francisco de Lacerda.</p></div>'
        event = museum.parse_detail(detail, record)[0]
        self.assertEqual(event["date"], dt.date(2026, 10, 6))
        self.assertEqual(event["end_date"], dt.date(2026, 11, 1))
        self.assertIn("exhibition", event["tags"])
        self.assertIsNone(event["time"])

    def test_blocked_non_archive_and_malformed_cards_fail(self):
        for payload in (b'<title>Just a moment</title>', ARCHIVE.replace(b'04.10.2026', b'31.02.2026')):
            with self.subTest(payload=payload), self.assertRaises(SourceError):
                museum.parse_archive(payload, museum.ARCHIVES[0])
        with self.assertRaises(SourceError):
            museum.parse_detail(b'<p>Login required</p>', {"source_url": "https://example.test"})

    def test_changed_archive_schema_does_not_become_healthy_empty(self):
        for payload in (ARCHIVE.replace(b'card-title', b'event-title'),
                        ARCHIVE.replace(b'small mt-auto', b'event-date'),
                        ARCHIVE.replace(b'04.10.2026 - 25.10.2026', b''), b'<h1>Eventos</h1>'):
            with self.subTest(payload=payload), self.assertRaises(SourceError):
                museum.parse_archive(payload, museum.ARCHIVES[0])

    def test_archive_keeps_every_explicit_session(self):
        payload = ARCHIVE.replace(b'04.10.2026 - 25.10.2026', b'03.10.2026, 10.10.2026')
        records, _ = museum.parse_archive(payload, museum.ARCHIVES[0])
        self.assertEqual([record["date"] for record in records], [dt.date(2026, 10, 3), dt.date(2026, 10, 10)])

    def test_explicit_second_workshop_date_overrides_administrative_end(self):
        record = {"name": "Oficina de pintura", "date": dt.date(2026, 10, 3),
                  "end_date": dt.date(2026, 10, 17), "source_url": museum.BASE_URL + "/events/oficina/"}
        detail = '''<div class="post-content"><p>Oficina em duas sessões.</p>
        <p>MUSEU DE ANGRA DO HEROÍSMO. 14H00. Segunda sessão a 10 de outubro.</p></div>'''.encode()
        events = museum.parse_detail(detail, record)
        self.assertEqual([event["date"] for event in events], [dt.date(2026, 10, 3), dt.date(2026, 10, 10)])

    def test_restricted_continuation_is_excluded(self):
        record = museum.parse_archive(ARCHIVE, museum.ARCHIVES[0])[0][0]
        detail = b'<div class="post-content"><p>Inscri\xc3\xa7\xc3\xa3o v\xc3\xa1lida apenas para quem participou na primeira sess\xc3\xa3o.</p></div>'
        self.assertEqual(museum.parse_detail(detail, record), [])

    def test_all_archives_and_pages_are_followed(self):
        health = SourceHealth("test")
        responses = {museum.ARCHIVES[0]: ARCHIVE, museum.ARCHIVES[1]: b'<h1>Exposi\xc3\xa7\xc3\xb5es</h1><p>Nenhuma exposi\xc3\xa7\xc3\xa3o encontrada</p>',
                     museum.ARCHIVES[2]: b'<h1>Exposi\xc3\xa7\xc3\xb5es</h1><p>Nenhuma exposi\xc3\xa7\xc3\xa3o encontrada</p>',
                     museum.BASE_URL + "/events/page/2/": b'<h1>Eventos</h1><p>Nenhum evento encontrado</p>',
                     museum.BASE_URL + "/events/domingos-com-musica-52/": DETAIL}
        with patch.object(health, "fetch", side_effect=lambda url: responses[url]) as fetch:
            events = museum.discover_events(dt.date(2026, 10, 10), dt.date(2027, 1, 1), health)
        self.assertEqual(len(events), 4)
        self.assertIn(museum.BASE_URL + "/events/page/2/", [call.args[0] for call in fetch.call_args_list])


if __name__ == "__main__":
    unittest.main()
