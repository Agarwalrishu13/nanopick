"""nanoPick's tests, end to end: real folders, real search, real copies.

Three layers: the finder's judgement about words and kinds, the actions'
promise that nothing is ever moved or overwritten, and the whole app over
real HTTP — including the rule that another website must not be able to drive
it, and that a made-up path cannot smuggle a file out through a preview.
"""

import json
import os
import shutil
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from pathlib import Path

from nanopick import actions, finder, server, store


class FinderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("receipt-november.jpg", "jpeg")
        self.write("Holiday Photo.png", "png")
        self.write("project report.pdf", "%PDF-1.4")
        self.write("song.mp3", "mp3")
        self.write("clip.mp4", "video")
        self.write("bundle.zip", "zip")
        self.write("notes.txt", "hello")
        time.sleep(0.05)
        self.write("fresh-thing.txt", "new")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def search(self, **kwargs):
        kwargs.setdefault("roots", [self.root])
        if "q" in kwargs:
            kwargs["query"] = kwargs.pop("q")
        return finder.search(**kwargs)

    def names(self, **kwargs):
        return [item["name"] for item in self.search(**kwargs)["results"]]

    # -- matching ----------------------------------------------------------
    def test_one_word_matches_anywhere_in_the_name(self):
        self.assertIn("receipt-november.jpg", self.names(q="receipt"))

    def test_matching_ignores_capitals(self):
        self.assertIn("Holiday Photo.png", self.names(q="holiday photo"))

    def test_every_word_must_be_present(self):
        self.assertIn("receipt-november.jpg", self.names(q="november receipt"))
        self.assertNotIn("receipt-november.jpg", self.names(q="receipt december"))

    def test_no_words_means_newest_first(self):
        results = self.search(q="")
        self.assertTrue(results["total"] > 0)
        mtimes = [item["mtime"] for item in results["results"]]
        self.assertEqual(mtimes, sorted(mtimes, reverse=True))

    # -- kinds -------------------------------------------------------------
    def test_kinds_are_what_a_person_calls_them(self):
        self.assertEqual(finder.kind_of("x.jpg"), "pictures")
        self.assertEqual(finder.kind_of("x.PDF"), "documents")
        self.assertEqual(finder.kind_of("x.mp3"), "music")
        self.assertEqual(finder.kind_of("x.mp4"), "video")
        self.assertEqual(finder.kind_of("x.zip"), "archives")
        self.assertEqual(finder.kind_of("x.xyzzy"), "other")

    def test_a_kind_filter_keeps_only_that_kind(self):
        self.assertEqual(self.names(q="", kind="music"), ["song.mp3"])
        self.assertIn("project report.pdf", self.names(q="", kind="documents"))
        self.assertNotIn("song.mp3", self.names(q="", kind="documents"))

    # -- when --------------------------------------------------------------
    def test_a_thing_just_written_is_in_today(self):
        self.assertIn("fresh-thing.txt", self.names(q="", when="today"))
        self.assertNotIn("fresh-thing.txt", self.names(q="", when="older"))

    def test_every_result_knows_its_bucket(self):
        data = self.search(q="fresh")
        self.assertEqual(data["results"][0]["when_bucket"], "today")

    # -- answers -----------------------------------------------------------
    def test_answers_come_in_plain_words(self):
        data = self.search(q="receipt")
        one = data["results"][0]
        self.assertEqual(one["what"], "a picture")
        self.assertTrue(one["when"].endswith(("ago", "now", "yesterday")))
        self.assertTrue(one["size_text"].endswith(("bytes", "KB", "MB", "GB")))

    def test_nothing_found_is_an_empty_answer_not_an_error(self):
        data = self.search(q="definitely-not-here-xyz")
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["results"], [])

    def test_a_search_cannot_run_away(self):
        data = self.search(q="")
        self.assertLessEqual(data["shown"], finder.MAX_RESULTS)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env_patch = unittest.mock.patch.dict(os.environ, {"NANOPICK_HOME": self._tmp.name})
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

    def test_settings_start_empty_and_sensible(self):
        settings = store.settings()
        self.assertEqual(settings["destination"], "")
        self.assertEqual(settings["roots"], [])

    def test_roots_that_do_not_exist_are_never_remembered(self):
        saved = store.save_settings({"roots": [self._tmp.name, r"Z:\definitely\not\here"]})
        self.assertEqual(saved["roots"], [str(Path(self._tmp.name).resolve())])

    def test_the_usual_roots_are_used_when_nothing_is_remembered(self):
        self.assertTrue(store.search_roots())


import unittest.mock  # noqa: E402  (used above)


class ActionsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "stuff"
        self.root.mkdir()
        self.destination = Path(self._tmp.name) / "project"
        self.destination.mkdir()
        self.file = self.root / "report.pdf"
        self.file.write_text("%PDF-1.4 hello", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_copy_leaves_the_original_alone(self):
        result = actions.copy_to(self.file, self.destination)
        self.assertTrue(result["ok"], result)
        self.assertTrue(self.file.exists(), "the original vanished!")
        self.assertEqual((self.destination / "report.pdf").read_text(encoding="utf-8"), "%PDF-1.4 hello")

    def test_a_second_copy_does_not_overwrite_the_first(self):
        actions.copy_to(self.file, self.destination)
        result = actions.copy_to(self.file, self.destination)
        self.assertTrue(result["ok"], result)
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()),
                         ["report (2).pdf", "report.pdf"])

    def test_copying_into_a_folder_that_is_not_there_is_explained(self):
        result = actions.copy_to(self.file, self.destination / "nope")
        self.assertFalse(result["ok"])
        self.assertIn("no folder", result["said"].lower())

    def test_opening_a_file_that_is_gone_is_explained(self):
        result = actions.open_file(self.file / "not-really")
        self.assertFalse(result["ok"])

    def test_revealing_a_file_that_is_gone_is_explained(self):
        result = actions.reveal(self.root / "vanished.pdf")
        self.assertFalse(result["ok"])

    def test_packing_makes_a_zip_with_everything_in_it(self):
        second = self.root / "photo.jpg"
        second.write_bytes(b"jpeg")
        result = actions.pack([self.file, second], self.destination)
        self.assertTrue(result["ok"], result)
        made = Path(result["packed_to"])
        self.assertTrue(made.exists())
        with zipfile.ZipFile(made) as bundle:
            self.assertEqual(sorted(bundle.namelist()), ["photo.jpg", "report.pdf"])

    def test_packing_skips_what_is_not_a_file_and_says_so(self):
        ghost = self.root / "ghost.pdf"
        result = actions.pack([self.file, ghost], self.destination)
        self.assertTrue(result["ok"])
        self.assertIn("left out", result["said"])

    def test_packing_nothing_is_explained(self):
        self.assertFalse(actions.pack([], self.destination)["ok"])


class ServerTestCase(unittest.TestCase):
    """The whole app over real HTTP, on this machine only."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._home = unittest.mock.patch.dict(os.environ, {"NANOPICK_HOME": str(Path(cls._tmp.name) / "home")})
        cls._home.start()
        cls.root = Path(cls._tmp.name) / "files"
        cls.root.mkdir()
        (cls.root / "receipt.jpg").write_bytes(b"jpeg")
        (cls.root / "notes.txt").write_text("hello world", encoding="utf-8")
        (cls.root / "report.pdf").write_text("%PDF-1.4", encoding="utf-8")
        store.save_settings({"roots": [str(cls.root)],
                             "destination": str(Path(cls._tmp.name) / "project")})
        Path(cls._tmp.name, "project").mkdir()

        import nanopick.httpbase as httpbase
        cls.app = server.create_app()
        cls.port = httpbase.free_port(8779)
        cls.base = "http://127.0.0.1:%d" % cls.port
        threading.Thread(target=cls.app.serve, kwargs={
            "host": "127.0.0.1", "port": cls.port, "open_browser": False, "quiet": True,
        }, daemon=True).start()
        for _ in range(80):
            try:
                cls.get("/api/health")
                return
            except Exception:
                time.sleep(0.05)
        raise RuntimeError("the test server never came up")

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls._home.stop()
        cls._tmp.cleanup()

    @classmethod
    def get(cls, path, headers=None):
        request = urllib.request.Request(cls.base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read(), response.status
        except urllib.error.HTTPError as exc:
            return exc.read(), exc.code

    @classmethod
    def post(cls, path, payload=None, headers=None):
        request = urllib.request.Request(
            cls.base + path, data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read(), response.status
        except urllib.error.HTTPError as exc:
            return exc.read(), exc.code

    def body(self, raw):
        return json.loads(raw.decode("utf-8"))


class ServerBasicsTests(ServerTestCase):
    def test_health_says_who_it_is(self):
        raw, status = self.get("/api/health")
        self.assertEqual(status, 200)
        data = self.body(raw)
        self.assertEqual(data["app"], "nanoPick")
        self.assertIn(str(Path(self.root).resolve()), data["roots"])

    def test_search_over_http_finds_the_file(self):
        raw, status = self.get("/api/search?q=receipt")
        self.assertEqual(status, 200)
        names = [item["name"] for item in self.body(raw)["results"]]
        self.assertEqual(names, ["receipt.jpg"])

    def test_a_search_is_recorded_as_the_last_search(self):
        self.get("/api/search?q=remembered-thing")
        self.assertEqual(store.settings()["last_search"], "remembered-thing")


class PreviewGuardTests(ServerTestCase):
    def test_a_text_file_previews_as_text(self):
        raw, status = self.get("/api/preview?path=" + urllib.request.quote(str(self.root / "notes.txt")))
        self.assertEqual(status, 200)
        self.assertIn(b"hello world", raw)

    def test_an_image_previews_with_its_type(self):
        raw, status = self.get("/api/preview?path=" + urllib.request.quote(str(self.root / "receipt.jpg")))
        self.assertEqual(status, 200)
        self.assertEqual(raw, b"jpeg")

    def test_a_file_outside_the_roots_is_refused(self):
        outside = Path(self._tmp.name) / "secret.txt"
        outside.write_text("private", encoding="utf-8")
        raw, status = self.get("/api/preview?path=" + urllib.request.quote(str(outside)))
        self.assertEqual(status, 400)
        self.assertIn("not allowed", self.body(raw)["error"])

    def test_a_path_that_is_not_a_file_is_refused(self):
        raw, status = self.get("/api/preview?path=" + urllib.request.quote(str(self.root)))
        self.assertEqual(status, 400)


class LocalPageGuardTests(ServerTestCase):
    """Another website must not be able to drive this app."""

    def test_an_action_from_a_foreign_page_is_refused(self):
        raw, status = self.post("/api/open", {"path": str(self.root / "notes.txt")},
                                headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)

    def test_a_mutation_without_json_is_refused(self):
        request = urllib.request.Request(
            self.base + "/api/pack", data=b"hello", method="POST",
            headers={"Content-Type": "text/plain", "Origin": self.base})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        self.assertEqual(status, 403)

    def test_the_app_its_own_page_is_allowed(self):
        raw, status = self.post("/api/reveal", {"path": str(self.root / "notes.txt")},
                                headers={"Origin": self.base})
        self.assertEqual(status, 200)


class CopyAndPackOverHttpTests(ServerTestCase):
    def test_a_copy_arrives_in_the_destination(self):
        raw, status = self.post("/api/copy", {"path": str(self.root / "report.pdf")})
        self.assertEqual(status, 200)
        data = self.body(raw)
        self.assertTrue(data["ok"], data)
        self.assertTrue(Path(data["copied_to"]).exists())

    def test_copying_without_a_destination_is_explained(self):
        store.save_settings({"destination": ""})
        try:
            raw, status = self.post("/api/copy", {"path": str(self.root / "report.pdf")})
            self.assertEqual(status, 400)
            self.assertIn("where", self.body(raw)["error"])
        finally:
            store.save_settings({"destination": str(Path(self._tmp.name) / "project")})

    def test_packing_over_http_makes_a_real_zip(self):
        raw, status = self.post("/api/pack", {"paths": [str(self.root / "receipt.jpg")]})
        self.assertEqual(status, 200)
        data = self.body(raw)
        self.assertTrue(data["ok"], data)
        made = Path(data["packed_to"])
        try:
            with zipfile.ZipFile(made) as bundle:
                self.assertEqual(bundle.namelist(), ["receipt.jpg"])
        finally:
            made.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()


class ContentSearchTests(unittest.TestCase):
    """Looking inside files: the honest kind of 'search the contents'."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "diary.txt").write_text(
            "line one\nthe receipt was on the table\nlast line", encoding="utf-8")
        (self.root / "code.py").write_text(
            "def main():\n    print('receipt check')\n", encoding="utf-8")
        (self.root / "photo.jpg").write_bytes(b"jpeg")  # never read

    def tearDown(self):
        self._tmp.cleanup()

    def names(self, q):
        return [m["name"] for m in finder.search_inside(q, roots=[self.root])["matches"]]

    def test_a_word_inside_a_file_is_found_with_its_line(self):
        got = finder.search_inside("receipt", roots=[self.root])["matches"]
        self.assertEqual(len(got), 2)  # diary.txt and code.py both say it
        diary = next(m for m in got if m["name"] == "diary.txt")
        self.assertEqual(diary["line"], 2)
        self.assertIn("receipt", diary["snippet"])

    def test_every_word_must_be_present_in_the_line(self):
        self.assertEqual(self.names("receipt table"), ["diary.txt"])
        self.assertEqual(self.names("receipt table moon"), [])

    def test_binary_files_are_never_read(self):
        self.assertEqual(self.names("jpeg"), [])  # the bytes of photo.jpg are not searched

    def test_empty_words_is_polite_not_an_error(self):
        result = finder.search_inside("", roots=[self.root])
        self.assertEqual(result["total"], 0)
        self.assertTrue(result["why"])

