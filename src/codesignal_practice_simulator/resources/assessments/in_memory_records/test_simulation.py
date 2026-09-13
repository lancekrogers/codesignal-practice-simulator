import unittest

from simulation import simulate


def q(text):
    """Turn a whitespace-separated query block into the query list."""
    return [line.split() for line in text.strip().splitlines() if line.strip()]


class TestSimulateCodingFramework(unittest.TestCase):
    def test_group_1(self):
        self.assertEqual(
            simulate(q("""
                SET users alice admin
                SET users bob viewer
                GET users alice
                GET users carol
                GET groups alice
                DELETE users alice
                DELETE users alice
                DELETE users bob
                SET users bob editor
            """)),
            ["true", "false", "admin", "", "", "true", "false", "true", "true"],
        )
        self.assertEqual(
            simulate(q("""
                SET r f 0
                SET r f 0
                SET r f 00
                GET r f
                DELETE r g
                DELETE missing f
                DELETE r f
                GET r f
                SET r f again
            """)),
            ["true", "false", "false", "00", "false", "false", "true", "", "true"],
        )
        self.assertEqual(simulate([]), [])
        with self.assertRaises(ValueError):
            simulate([["GET", "users"]])
        with self.assertRaises(ValueError):
            simulate([["FETCH", "users", "alice"]])
        with self.assertRaises(ValueError):
            simulate([["SET", "users", "alice", "admin", "extra"]])

    def test_group_2(self):
        self.assertEqual(
            simulate(q("""
                SET cfg zeta 1
                SET cfg alpha 2
                SET cfg Alpha 3
                SET cfg alpha2 4
                SCAN cfg
                SCAN_BY_PREFIX cfg al
                SCAN_BY_PREFIX cfg Z
                SCAN nothing
                SCAN_BY_PREFIX nothing a
            """)),
            [
                "true", "false", "false", "false",
                "Alpha(3), alpha(2), alpha2(4), zeta(1)",
                "alpha(2), alpha2(4)",
                "",
                "",
                "",
            ],
        )
        self.assertEqual(
            simulate(q("""
                SET n a10 x
                SET n a2 y
                SET n a1 z
                SET n a w
                SCAN n
                SCAN_BY_PREFIX n a1
                DELETE n a10
                DELETE n a2
                DELETE n a1
                SCAN n
                DELETE n a
                SCAN n
                SET n only v
                SCAN n
            """)),
            [
                "true", "false", "false", "false",
                "a(w), a1(z), a10(x), a2(y)",
                "a1(z), a10(x)",
                "true", "true", "true",
                "a(w)",
                "true",
                "",
                "true",
                "only(v)",
            ],
        )
        with self.assertRaises(ValueError):
            simulate([["SCAN"]])

    def test_group_3(self):
        self.assertEqual(
            simulate(q("""
                SET_AT_WITH_TTL 1 s a 1 5
                SET_AT 2 s b 2
                GET_AT 5 s a
                GET_AT 6 s a
                SCAN_AT 6 s
                DELETE_AT 7 s a
                SET_AT_WITH_TTL 8 s b 9 1
                SCAN_AT 9 s
                SET_AT 9 s c 3
            """)),
            ["true", "false", "1", "", "b(2)", "false", "false", "", "true"],
        )
        self.assertEqual(
            simulate(q("""
                SET_AT_WITH_TTL 10 t x 1 4
                SET_AT_WITH_TTL 10 t y 2 4
                SET_AT_WITH_TTL 11 t z 3 1
                SCAN_AT 11 t
                SCAN_AT 12 t
                SCAN_BY_PREFIX_AT 13 t x
                SCAN_AT 14 t
                GET_AT 14 t x
                SET_AT_WITH_TTL 14 t x 5 2
                SET_AT 15 t x 6
                GET_AT 100 t x
                DELETE_AT 100 t x
                SCAN_AT 100 t
            """)),
            [
                "true", "false", "false",
                "x(1), y(2), z(3)",
                "x(1), y(2)",
                "x(1)",
                "",
                "",
                "true",
                "false",
                "6",
                "true",
                "",
            ],
        )
        with self.assertRaises(ValueError):
            simulate([["SET_AT_WITH_TTL", "1", "s", "a", "v"]])

    def test_group_4(self):
        self.assertEqual(
            simulate(q("""
                SET_AT_WITH_TTL 1 r x 1 10
                SET_AT 2 r y 2
                BACKUP 5
                DELETE_AT 6 r y
                SET_AT 7 q z 9
                BACKUP 8
                RESTORE 20 6
                SCAN_AT 20 r
                SCAN_AT 20 q
                GET_AT 26 r x
                RESTORE 30 4
            """)),
            [
                "true", "false", "1", "true", "true", "2", "true",
                "x(1), y(2)", "", "", "false",
            ],
        )
        self.assertEqual(
            simulate(q("""
                BACKUP 1
                SET_AT 2 a f v
                BACKUP 3
                SET_AT 3 b g w
                BACKUP 3
                RESTORE 4 3
                SCAN_AT 4 b
                RESTORE 5 1
                SCAN_AT 5 a
                SCAN_AT 5 b
                BACKUP 6
                SET_AT_WITH_TTL 7 c h u 3
                BACKUP 8
                RESTORE 50 8
                GET_AT 51 c h
                GET_AT 52 c h
                BACKUP 52
            """)),
            [
                "0", "true", "1", "true", "2", "true", "g(w)", "true", "", "",
                "0", "true", "1", "true", "u", "", "0",
            ],
        )
        with self.assertRaises(ValueError):
            simulate([["RESTORE", "1"]])


if __name__ == "__main__":
    unittest.main()
