"""Tests for the behaviour level{1..4}.md describes.

`test_simulation.py` (shipped with the assessment) only checks the happy path
of four fixed scripts, and its level-4 expectations contradict the level-4
spec.  This suite covers the rules the prose states and the edges a real grader
would probe: duplicate uploads, missing sources, the TTL boundary, the search
cap, and a rollback that actually rolls back.
"""

import unittest

from simulation import (
    FILE_NOT_FOUND,
    ROLLBACK_RESTORE,
    FileStorage,
    parse_size,
    simulate_coding_framework,
)


class TestSizeParsing(unittest.TestCase):
    def test_units_are_normalised_to_bytes(self):
        self.assertEqual(parse_size("200kb"), 200 * 1024)
        self.assertEqual(parse_size("2MB"), 2 * 1024**2)
        self.assertEqual(parse_size("512"), 512)
        self.assertEqual(parse_size(4321), 4321)

    def test_sizes_compare_numerically_not_lexicographically(self):
        # "9kb" > "10mb" as strings; the whole point of parsing.
        self.assertGreater(parse_size("10mb"), parse_size("9kb"))

    def test_unparseable_size_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_size("big")


class TestLevel1(unittest.TestCase):
    def setUp(self):
        self.storage = FileStorage()

    def test_upload_then_get_returns_size(self):
        self.storage.upload("Cars.txt", "200kb")
        self.assertEqual(self.storage.get("Cars.txt"), "200kb")

    def test_get_missing_file_returns_nothing(self):
        self.assertIsNone(self.storage.get("Nope.txt"))

    def test_duplicate_upload_raises(self):
        self.storage.upload("Cars.txt", "200kb")
        with self.assertRaises(RuntimeError):
            self.storage.upload("Cars.txt", "300kb")

    def test_copy_missing_source_raises(self):
        with self.assertRaises(RuntimeError):
            self.storage.copy("Ghost.txt", "Copy.txt")

    def test_copy_overwrites_existing_destination(self):
        self.storage.upload("Cars.txt", "200kb")
        self.storage.upload("Bikes.txt", "50kb")
        self.storage.copy("Cars.txt", "Bikes.txt")
        self.assertEqual(self.storage.get("Bikes.txt"), "200kb")

    def test_missing_get_is_reported_in_the_output_log(self):
        self.assertEqual(
            simulate_coding_framework([["FILE_GET", "Ghost.txt"]]), [FILE_NOT_FOUND]
        )


class TestLevel2(unittest.TestCase):
    def setUp(self):
        self.storage = FileStorage()

    def test_orders_by_size_descending_then_name(self):
        self.storage.upload("Ba1.txt", "100kb")
        self.storage.upload("Ba2.txt", "300kb")
        self.storage.upload("Ba0.txt", "300kb")  # ties with Ba2 on size
        self.assertEqual(self.storage.search("Ba"), ["Ba0.txt", "Ba2.txt", "Ba1.txt"])

    def test_returns_at_most_ten_files(self):
        for index in range(15):
            self.storage.upload(f"File{index:02d}.txt", f"{index + 1}kb")
        results = self.storage.search("File")
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0], "File14.txt")  # largest
        self.assertEqual(results[-1], "File05.txt")  # tenth largest

    def test_prefix_must_match_the_start_of_the_name(self):
        self.storage.upload("Cars.txt", "200kb")
        self.assertEqual(self.storage.search("ars"), [])
        self.assertEqual(self.storage.search("Zz"), [])


class TestLevel3(unittest.TestCase):
    def setUp(self):
        self.storage = FileStorage()
        self.noon = "2021-07-01T12:00:00"

    def test_file_without_ttl_lives_forever(self):
        self.storage.upload_at(self.noon, "Python.txt", "150kb")
        self.assertEqual(
            self.storage.get_at("2031-07-01T12:00:00", "Python.txt"), "150kb"
        )

    def test_ttl_boundary_is_half_open(self):
        self.storage.upload_at(self.noon, "Short.txt", "10kb", 60)
        self.assertIsNotNone(self.storage.get_at("2021-07-01T12:00:59", "Short.txt"))
        self.assertIsNone(self.storage.get_at("2021-07-01T12:01:00", "Short.txt"))

    def test_expired_files_are_hidden_from_search(self):
        self.storage.upload_at(self.noon, "Alive.txt", "10kb")
        self.storage.upload_at(self.noon, "Adead.txt", "99kb", 1)
        self.assertEqual(
            self.storage.search_at("2021-07-01T12:00:05", "A"), ["Alive.txt"]
        )

    def test_copy_dies_when_the_original_would_have(self):
        self.storage.upload_at(self.noon, "Source.txt", "10kb", 60)
        self.storage.copy_at("2021-07-01T12:00:30", "Source.txt", "Copy.txt")
        self.assertIsNotNone(self.storage.get_at("2021-07-01T12:00:59", "Copy.txt"))
        self.assertIsNone(self.storage.get_at("2021-07-01T12:01:00", "Copy.txt"))

    def test_expired_name_can_be_reused(self):
        self.storage.upload_at(self.noon, "Slot.txt", "10kb", 1)
        # Not a duplicate: the first file is gone by now.
        self.storage.upload_at("2021-07-01T12:00:05", "Slot.txt", "20kb")
        self.assertEqual(self.storage.get_at("2021-07-01T12:00:06", "Slot.txt"), "20kb")

    def test_copying_an_expired_source_raises(self):
        self.storage.upload_at(self.noon, "Gone.txt", "10kb", 1)
        with self.assertRaises(RuntimeError):
            self.storage.copy_at("2021-07-01T12:00:05", "Gone.txt", "Copy.txt")


class TestLevel4Rollback(unittest.TestCase):
    """Rollback as level4.md describes it: state really returns."""

    def setUp(self):
        self.storage = FileStorage()  # ROLLBACK_RESTORE is the default

    def test_files_created_after_the_target_are_dropped(self):
        self.storage.upload_at("2021-07-01T12:00:00", "Initial.txt", "100kb")
        self.storage.upload_at("2021-07-01T12:20:00", "Later.txt", "200kb")
        self.storage.rollback("2021-07-01T12:10:00")
        self.assertIsNotNone(self.storage.get_at("2021-07-01T12:25:00", "Initial.txt"))
        self.assertIsNone(self.storage.get_at("2021-07-01T12:25:00", "Later.txt"))

    def test_copies_made_after_the_target_are_dropped(self):
        self.storage.upload_at("2021-07-01T12:00:00", "Update1.txt", "150kb", 3600)
        self.storage.copy_at("2021-07-01T12:15:00", "Update1.txt", "Update1Copy.txt")
        self.storage.rollback("2021-07-01T12:10:00")
        self.assertEqual(
            self.storage.search_at("2021-07-01T12:25:00", "Up"), ["Update1.txt"]
        )

    def test_operations_exactly_at_the_target_are_kept(self):
        self.storage.upload_at("2021-07-01T12:10:00", "OnTheDot.txt", "10kb")
        self.storage.rollback("2021-07-01T12:10:00")
        self.assertIsNotNone(self.storage.get_at("2021-07-01T12:10:00", "OnTheDot.txt"))

    def test_ttls_are_recalculated_from_the_original_upload(self):
        self.storage.upload_at("2021-07-01T12:05:00", "Update1.txt", "150kb", 3600)
        self.storage.rollback("2021-07-01T12:10:00")
        # Still expires 3600s after its *upload*, not after the rollback.
        self.assertIsNotNone(self.storage.get_at("2021-07-01T13:04:59", "Update1.txt"))
        self.assertIsNone(self.storage.get_at("2021-07-01T13:05:00", "Update1.txt"))

    def test_a_file_that_had_already_expired_does_not_return(self):
        self.storage.upload_at("2021-07-01T12:00:00", "Brief.txt", "10kb", 60)
        self.storage.upload_at("2021-07-01T12:20:00", "Later.txt", "10kb")
        self.storage.rollback("2021-07-01T12:10:00")
        self.assertIsNone(self.storage.get_at("2021-07-01T12:10:00", "Brief.txt"))

    def test_rollback_is_repeatable(self):
        self.storage.upload_at("2021-07-01T12:00:00", "A.txt", "10kb")
        self.storage.upload_at("2021-07-01T12:10:00", "B.txt", "10kb")
        self.storage.upload_at("2021-07-01T12:20:00", "C.txt", "10kb")
        self.storage.rollback("2021-07-01T12:15:00")
        self.storage.rollback("2021-07-01T12:05:00")
        self.assertEqual(self.storage.search_at("2021-07-01T12:30:00", ""), ["A.txt"])

    def test_untimed_uploads_survive_any_rollback(self):
        self.storage.upload("Legacy.txt", "10kb")
        self.storage.rollback("2021-07-01T12:00:00")
        self.assertIsNotNone(self.storage.get("Legacy.txt"))


class TestBundledScriptUnderSpecSemantics(unittest.TestCase):
    """The bundled level-4 script, scored against the level-4 prose."""

    def test_group_4_with_real_rollback(self):
        script = [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Initial.txt", "100kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:05:00", "Update1.txt", "150kb", 3600],
            ["FILE_GET_AT", "2021-07-01T12:10:00", "Initial.txt"],
            ["FILE_COPY_AT", "2021-07-01T12:15:00", "Update1.txt", "Update1Copy.txt"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:20:00", "Update2.txt", "200kb", 1800],
            ["ROLLBACK", "2021-07-01T12:10:00"],
            ["FILE_GET_AT", "2021-07-01T12:25:00", "Update1.txt"],
            ["FILE_GET_AT", "2021-07-01T12:25:00", "Initial.txt"],
            ["FILE_SEARCH_AT", "2021-07-01T12:25:00", "Up"],
            ["FILE_GET_AT", "2021-07-01T12:25:00", "Update2.txt"],
        ]
        self.assertEqual(
            simulate_coding_framework(script, rollback_mode=ROLLBACK_RESTORE),
            [
                "uploaded at Initial.txt",
                "uploaded at Update1.txt",
                "got at Initial.txt",
                "copied at Update1.txt to Update1Copy.txt",
                "uploaded at Update2.txt",
                "rollback to 2021-07-01T12:10:00",
                "got at Update1.txt",
                "got at Initial.txt",
                # Update1Copy (12:15) and Update2 (12:20) were rolled away.
                "found at [Update1.txt]",
                FILE_NOT_FOUND,
            ],
        )


if __name__ == "__main__":
    unittest.main()
