"""Checks for the four simple, cumulative assessment solutions."""

import unittest

from stages import level1, level2, level3, level4


LEVEL_1_OPERATIONS = [
    ["FILE_UPLOAD", "Cars.txt", "200kb"],
    ["FILE_GET", "Cars.txt"],
    ["FILE_COPY", "Cars.txt", "Cars2.txt"],
    ["FILE_GET", "Cars2.txt"],
]

LEVEL_1_OUTPUT = [
    "uploaded Cars.txt",
    "got Cars.txt",
    "copied Cars.txt to Cars2.txt",
    "got Cars2.txt",
]

LEVEL_2_OPERATIONS = [
    ["FILE_UPLOAD", "Foo.txt", "100kb"],
    ["FILE_UPLOAD", "Bar.csv", "200kb"],
    ["FILE_UPLOAD", "Baz.pdf", "300kb"],
    ["FILE_SEARCH", "Ba"],
]

LEVEL_3_OPERATIONS = [
    ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Python.txt", "150kb"],
    ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "CodeSignal.txt", "150kb", 3600],
    ["FILE_GET_AT", "2021-07-01T13:00:01", "Python.txt"],
    ["FILE_COPY_AT", "2021-07-01T12:00:00", "Python.txt", "PythonCopy.txt"],
    ["FILE_SEARCH_AT", "2021-07-01T12:00:00", "Py"],
    ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Expired.txt", "100kb", 1],
    ["FILE_GET_AT", "2021-07-01T12:00:02", "Expired.txt"],
]


class TestLevel1(unittest.TestCase):
    def test_basic_operations(self):
        self.assertEqual(
            level1.simulate_coding_framework(LEVEL_1_OPERATIONS),
            LEVEL_1_OUTPUT,
        )

    def test_duplicate_upload_raises(self):
        with self.assertRaises(RuntimeError):
            level1.simulate_coding_framework(
                [
                    ["FILE_UPLOAD", "Cars.txt", "200kb"],
                    ["FILE_UPLOAD", "Cars.txt", "300kb"],
                ]
            )

    def test_copy_overwrites_destination(self):
        operations = [
            ["FILE_UPLOAD", "A.txt", "10kb"],
            ["FILE_UPLOAD", "B.txt", "20kb"],
            ["FILE_COPY", "A.txt", "B.txt"],
            ["FILE_GET", "B.txt"],
        ]
        self.assertEqual(
            level1.simulate_coding_framework(operations)[-2:],
            ["copied A.txt to B.txt", "got B.txt"],
        )


class TestLevel2(unittest.TestCase):
    def test_keeps_level_1_working(self):
        self.assertEqual(
            level2.simulate_coding_framework(LEVEL_1_OPERATIONS),
            LEVEL_1_OUTPUT,
        )

    def test_searches_by_size_then_name(self):
        operations = [
            ["FILE_UPLOAD", "BigB.txt", "100kb"],
            ["FILE_UPLOAD", "Small.txt", "9kb"],
            ["FILE_UPLOAD", "BigA.txt", "100kb"],
            ["FILE_SEARCH", ""],
        ]
        self.assertEqual(
            level2.simulate_coding_framework(operations)[-1],
            "found [BigA.txt, BigB.txt, Small.txt]",
        )

    def test_vendor_example(self):
        self.assertEqual(
            level2.simulate_coding_framework(LEVEL_2_OPERATIONS)[-1],
            "found [Baz.pdf, Bar.csv]",
        )


class TestLevel3(unittest.TestCase):
    def test_keeps_earlier_levels_working(self):
        self.assertEqual(
            level3.simulate_coding_framework(LEVEL_1_OPERATIONS),
            LEVEL_1_OUTPUT,
        )
        self.assertEqual(
            level3.simulate_coding_framework(LEVEL_2_OPERATIONS)[-1],
            "found [Baz.pdf, Bar.csv]",
        )

    def test_timestamped_operations_and_expiration(self):
        self.assertEqual(
            level3.simulate_coding_framework(LEVEL_3_OPERATIONS),
            [
                "uploaded at Python.txt",
                "uploaded at CodeSignal.txt",
                "got at Python.txt",
                "copied at Python.txt to PythonCopy.txt",
                "found at [Python.txt, PythonCopy.txt]",
                "uploaded at Expired.txt",
                "file not found",
            ],
        )

    def test_file_expires_exactly_at_ttl_boundary(self):
        operations = [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Short.txt", "1kb", 60],
            ["FILE_GET_AT", "2021-07-01T12:00:59", "Short.txt"],
            ["FILE_GET_AT", "2021-07-01T12:01:00", "Short.txt"],
        ]
        self.assertEqual(
            level3.simulate_coding_framework(operations)[-2:],
            ["got at Short.txt", "file not found"],
        )


class TestLevel4(unittest.TestCase):
    def test_keeps_earlier_levels_working(self):
        self.assertEqual(
            level4.simulate_coding_framework(LEVEL_1_OPERATIONS),
            LEVEL_1_OUTPUT,
        )
        self.assertEqual(
            level4.simulate_coding_framework(LEVEL_3_OPERATIONS)[-1],
            "file not found",
        )

    def test_rollback_restores_the_requested_state(self):
        operations = [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Initial.txt", "100kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:05:00", "Update1.txt", "150kb", 3600],
            ["FILE_COPY_AT", "2021-07-01T12:15:00", "Update1.txt", "Update1Copy.txt"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:20:00", "Update2.txt", "200kb", 1800],
            ["ROLLBACK", "2021-07-01T12:10:00"],
            ["FILE_SEARCH_AT", "2021-07-01T12:25:00", "Up"],
            ["FILE_GET_AT", "2021-07-01T12:25:00", "Update2.txt"],
        ]
        self.assertEqual(
            level4.simulate_coding_framework(operations)[-3:],
            [
                "rollback to 2021-07-01T12:10:00",
                "found at [Update1.txt]",
                "file not found",
            ],
        )

    def test_rollback_can_be_repeated(self):
        operations = [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "A.txt", "10kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:10:00", "B.txt", "20kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:20:00", "C.txt", "30kb"],
            ["ROLLBACK", "2021-07-01T12:15:00"],
            ["ROLLBACK", "2021-07-01T12:05:00"],
            ["FILE_SEARCH_AT", "2021-07-01T12:30:00", ""],
        ]
        self.assertEqual(
            level4.simulate_coding_framework(operations)[-1],
            "found at [A.txt]",
        )


if __name__ == "__main__":
    unittest.main()
