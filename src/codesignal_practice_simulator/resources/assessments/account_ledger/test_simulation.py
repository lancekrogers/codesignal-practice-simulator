import unittest

from simulation import simulate


def q(text):
    """Turn a whitespace-separated query block into the query list."""
    return [line.split() for line in text.strip().splitlines() if line.strip()]


class TestSimulateCodingFramework(unittest.TestCase):
    def test_group_1(self):
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 acc1
                CREATE_ACCOUNT 1 acc1
                CREATE_ACCOUNT 2 acc2
                DEPOSIT 3 acc1 500
                DEPOSIT 3 acc9 10
                TRANSFER 4 acc1 acc2 200
                TRANSFER 4 acc1 acc2 400
                TRANSFER 5 acc1 acc1 1
            """)),
            ["true", "false", "true", "500", "", "300", "", ""],
        )
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 a
                CREATE_ACCOUNT 1 b
                DEPOSIT 2 a 0
                DEPOSIT 2 a 7
                TRANSFER 3 a b 0
                TRANSFER 3 a b 7
                TRANSFER 3 a b 1
                DEPOSIT 4 b 3
                TRANSFER 5 b a 10
                TRANSFER 5 b missing 1
                TRANSFER 5 missing b 1
            """)),
            ["true", "true", "", "7", "", "0", "", "10", "0", "", ""],
        )
        self.assertEqual(simulate([]), [])
        with self.assertRaises(ValueError):
            simulate([["DEPOSIT", "1", "acc1"]])
        with self.assertRaises(ValueError):
            simulate([["WITHDRAW", "1", "acc1", "5"]])
        with self.assertRaises(ValueError):
            simulate([["CREATE_ACCOUNT", "1", "acc1", "extra"]])

    def test_group_2(self):
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 a
                CREATE_ACCOUNT 1 b
                CREATE_ACCOUNT 1 c
                DEPOSIT 2 a 100
                DEPOSIT 2 b 100
                TRANSFER 3 a c 40
                TRANSFER 3 b c 40
                TRANSFER 4 a c 10
                TOP_OUTGOING 5 2
                TOP_OUTGOING 5 5
                TOP_OUTGOING 5 0
            """)),
            [
                "true", "true", "true", "100", "100", "60", "60", "50",
                "a(50), b(40)",
                "a(50), b(40), c(0)",
                "",
            ],
        )
        self.assertEqual(
            simulate(q("""
                TOP_OUTGOING 1 3
                CREATE_ACCOUNT 2 b
                CREATE_ACCOUNT 2 a
                CREATE_ACCOUNT 2 B
                DEPOSIT 3 b 50
                DEPOSIT 3 a 50
                DEPOSIT 3 B 50
                TRANSFER 4 b B 20
                TRANSFER 4 a B 20
                TRANSFER 4 B a 20
                TRANSFER 5 a B 999
                TOP_OUTGOING 6 10
                TOP_OUTGOING 6 1
            """)),
            [
                "", "true", "true", "true", "50", "50", "50", "30", "30", "70", "",
                "B(20), a(20), b(20)",
                "B(20)",
            ],
        )
        with self.assertRaises(ValueError):
            simulate([["TOP_OUTGOING", "1"]])

    def test_group_3(self):
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 src
                CREATE_ACCOUNT 1 dst
                DEPOSIT 2 src 100
                SCHEDULE_TRANSFER 3 src dst 60 10
                SCHEDULE_TRANSFER 3 src dst 60 10
                SCHEDULE_TRANSFER 3 src dst 5 3
                GET_SCHEDULE_STATUS 4 src schedule1
                CANCEL_TRANSFER 5 dst schedule2
                TRANSFER 10 src dst 1
                GET_SCHEDULE_STATUS 10 src schedule1
                GET_SCHEDULE_STATUS 10 src schedule2
                CANCEL_TRANSFER 11 src schedule2
                TOP_OUTGOING 11 1
            """)),
            [
                "true", "true", "100", "schedule1", "schedule2", "",
                "PENDING", "false", "39", "EXECUTED", "FAILED", "false", "src(61)",
            ],
        )
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 a
                CREATE_ACCOUNT 1 b
                DEPOSIT 1 a 10
                SCHEDULE_TRANSFER 2 a b 10 5
                SCHEDULE_TRANSFER 2 a b 10 5
                SCHEDULE_TRANSFER 2 a a 1 5
                SCHEDULE_TRANSFER 2 a b 0 5
                SCHEDULE_TRANSFER 2 a ghost 1 5
                GET_SCHEDULE_STATUS 3 a schedule3
                GET_SCHEDULE_STATUS 3 b schedule1
                CANCEL_TRANSFER 4 a schedule2
                CANCEL_TRANSFER 4 a schedule2
                GET_SCHEDULE_STATUS 4 a schedule2
                GET_SCHEDULE_STATUS 5 a schedule1
                DEPOSIT 5 b 1
                GET_SCHEDULE_STATUS 9 a schedule1
                SCHEDULE_TRANSFER 9 b a 11 12
                SCHEDULE_TRANSFER 9 b a 1 12
                TOP_OUTGOING 12 5
                GET_SCHEDULE_STATUS 12 b schedule3
                GET_SCHEDULE_STATUS 12 b schedule4
            """)),
            [
                "true", "true", "10", "schedule1", "schedule2", "", "", "",
                "", "", "true", "false", "CANCELLED", "EXECUTED", "11",
                "EXECUTED", "schedule3", "schedule4",
                "b(11), a(10)", "EXECUTED", "FAILED",
            ],
        )
        # Schedules due at different times inside one jump execute in time
        # order, not in creation order.
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 m
                CREATE_ACCOUNT 1 n
                DEPOSIT 1 m 15
                SCHEDULE_TRANSFER 2 m n 10 8
                SCHEDULE_TRANSFER 2 m n 10 5
                GET_SCHEDULE_STATUS 20 m schedule2
                GET_SCHEDULE_STATUS 20 m schedule1
                TOP_OUTGOING 20 2
            """)),
            ["true", "true", "15", "schedule1", "schedule2", "EXECUTED", "FAILED", "m(10), n(0)"],
        )
        with self.assertRaises(ValueError):
            simulate([["SCHEDULE_TRANSFER", "1", "a", "b", "5"]])

    def test_group_4(self):
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 a
                CREATE_ACCOUNT 1 b
                DEPOSIT 2 a 100
                TRANSFER 5 a b 30
                BALANCE_AT 6 a 1
                BALANCE_AT 6 a 4
                BALANCE_AT 6 a 5
                BALANCE_AT 6 a 7
                SCHEDULE_TRANSFER 6 a b 10 20
                CLOSE_ACCOUNT 8 a b
                GET_SCHEDULE_STATUS 8 a schedule1
                BALANCE_AT 9 a 8
                BALANCE_AT 9 b 8
                CREATE_ACCOUNT 10 a
                BALANCE_AT 11 a 9
                BALANCE_AT 11 a 10
                TOP_OUTGOING 11 2
            """)),
            [
                "true", "true", "100", "70", "0", "100", "70", "", "schedule1",
                "100", "CANCELLED", "", "100", "true", "", "0", "a(0), b(0)",
            ],
        )
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 x
                CREATE_ACCOUNT 1 y
                DEPOSIT 2 x 50
                SCHEDULE_TRANSFER 3 x y 20 6
                BALANCE_AT 7 x 5
                BALANCE_AT 7 x 6
                BALANCE_AT 7 y 6
                BALANCE_AT 7 y 0
                CLOSE_ACCOUNT 8 y x
                CLOSE_ACCOUNT 8 y x
                CLOSE_ACCOUNT 8 x x
                BALANCE_AT 9 x 8
                SCHEDULE_TRANSFER 9 x y 1 12
                CREATE_ACCOUNT 10 z
                CLOSE_ACCOUNT 11 z x
                GET_SCHEDULE_STATUS 12 x schedule2
                BALANCE_AT 12 x 12
                TOP_OUTGOING 12 3
            """)),
            [
                "true", "true", "50", "schedule1", "50", "30", "20", "",
                "50", "", "", "50", "", "true", "50", "", "50", "x(20)",
            ],
        )
        # Closing an account: a pending schedule targeting it fails when due, a
        # pending schedule owned by the heir is untouched, and the closed
        # account leaves the ranking.
        self.assertEqual(
            simulate(q("""
                CREATE_ACCOUNT 1 p
                CREATE_ACCOUNT 1 q
                CREATE_ACCOUNT 1 r
                DEPOSIT 2 p 100
                DEPOSIT 2 q 100
                SCHEDULE_TRANSFER 3 p q 10 20
                SCHEDULE_TRANSFER 3 q r 5 30
                SCHEDULE_TRANSFER 3 r p 1 40
                CLOSE_ACCOUNT 5 q r
                GET_SCHEDULE_STATUS 6 q schedule2
                GET_SCHEDULE_STATUS 6 r schedule3
                GET_SCHEDULE_STATUS 6 p schedule1
                GET_SCHEDULE_STATUS 21 p schedule1
                BALANCE_AT 21 p 21
                GET_SCHEDULE_STATUS 41 r schedule3
                BALANCE_AT 41 p 40
                TOP_OUTGOING 41 3
            """)),
            [
                "true", "true", "true", "100", "100",
                "schedule1", "schedule2", "schedule3",
                "100", "CANCELLED", "PENDING", "PENDING",
                "FAILED", "100", "EXECUTED", "101", "r(1), p(0)",
            ],
        )
        with self.assertRaises(ValueError):
            simulate([["BALANCE_AT", "1", "x"]])


if __name__ == "__main__":
    unittest.main()
