import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import playlist_lookup as lookup


class PlaylistLookupTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.song = dict(title="Ditto", artists=[dict(name="NewJeans")], album=dict(id="A", name="Ditto"))
        self.client.search.return_value = [self.song]
        self.client.get_album.return_value = dict(title="Ditto", year="2022", tracks=[self.song],
            thumbnails=[dict(url="https://example.test/album.jpg", width=544, height=544)])
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.job = Path(self.folder.name) / "job.json"
        self.original = (ROOT / "examples/playlist-job.json").read_bytes()
        self.job.write_bytes(self.original)

    def test_fill_and_retry(self):
        download = Mock(return_value=(b"cover", "jpg"))
        for _ in range(2):
            lookup.fill(self.job, "p03", "ditto", "newjeans", None, self.client, download)
        job = json.loads(self.job.read_text())
        item, = job["pages"][2]["items"]
        self.assertEqual(item["meta"], "NewJeans · 2022")
        self.assertEqual((self.job.parent / item["artwork_ref"]).read_bytes(), b"cover")
        self.assertEqual(job["source_ids"].count(item["source_id"]), 1)
        self.assertEqual(job["sources"][-1]["locator"], "https://music.youtube.com/browse/A")

    def test_ambiguous_edition_leaves_job_intact(self):
        self.client.search.return_value.append(dict(self.song, album=dict(id="B", name="Reissue")))
        with self.assertRaisesRegex(ValueError, "판본"):
            lookup.fill(self.job, "p03", "Ditto", "NewJeans", None, self.client)
        self.assertEqual(self.job.read_bytes(), self.original)
        self.assertEqual(lookup.resolve(self.client, "Ditto", "NewJeans", "A")["year"], "2022")

    def test_album_fallback_verifies_track_credit(self):
        album = dict(title="Ditto", artists=self.song["artists"], browseId="A")
        self.client.search.side_effect = [[], [album]]
        self.assertEqual(lookup.resolve(self.client, "Ditto", "NewJeans")["album"], "Ditto")
        self.client.get_album.return_value["tracks"] = [dict(self.song, artists=[dict(name="Cover Band")])]
        self.client.search.side_effect = [[], [album]]
        with self.assertRaises(ValueError):
            lookup.resolve(self.client, "Ditto", "NewJeans")

    def test_missing_year_or_failed_download_preserves_job(self):
        with self.assertRaises(OSError):
            lookup.fill(self.job, "p03", "Ditto", "NewJeans", None, self.client, Mock(side_effect=OSError()))
        self.client.get_album.return_value["year"] = None
        with self.assertRaises(ValueError):
            lookup.fill(self.job, "p03", "Ditto", "NewJeans", None, self.client)
        self.assertEqual(self.job.read_bytes(), self.original)
