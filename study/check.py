"""Run cumulative assessment checks against any solution file."""

import importlib.util
import sys
from pathlib import Path


CASES = {
    1: (
        [
            ["FILE_UPLOAD", "Cars.txt", "200kb"],
            ["FILE_GET", "Cars.txt"],
            ["FILE_COPY", "Cars.txt", "Cars2.txt"],
            ["FILE_GET", "Cars2.txt"],
            ["FILE_GET", "Missing.txt"],
        ],
        [
            "uploaded Cars.txt",
            "got Cars.txt",
            "copied Cars.txt to Cars2.txt",
            "got Cars2.txt",
            "file not found",
        ],
    ),
    2: (
        [
            ["FILE_UPLOAD", "BaZ.txt", "9kb"],
            ["FILE_UPLOAD", "BaB.txt", "100kb"],
            ["FILE_UPLOAD", "BaA.txt", "100kb"],
            ["FILE_SEARCH", "Ba"],
        ],
        [
            "uploaded BaZ.txt",
            "uploaded BaB.txt",
            "uploaded BaA.txt",
            "found [BaA.txt, BaB.txt, BaZ.txt]",
        ],
    ),
    3: (
        [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Long.txt", "150kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "Short.txt", "200kb", 60],
            ["FILE_GET_AT", "2021-07-01T12:00:59", "Short.txt"],
            ["FILE_GET_AT", "2021-07-01T12:01:00", "Short.txt"],
            ["FILE_SEARCH_AT", "2021-07-01T12:01:00", ""],
        ],
        [
            "uploaded at Long.txt",
            "uploaded at Short.txt",
            "got at Short.txt",
            "file not found",
            "found at [Long.txt]",
        ],
    ),
    4: (
        [
            ["FILE_UPLOAD_AT", "2021-07-01T12:00:00", "First.txt", "100kb"],
            ["FILE_UPLOAD_AT", "2021-07-01T12:10:00", "Second.txt", "200kb"],
            ["FILE_COPY_AT", "2021-07-01T12:20:00", "Second.txt", "Copy.txt"],
            ["ROLLBACK", "2021-07-01T12:10:00"],
            ["FILE_SEARCH_AT", "2021-07-01T12:30:00", ""],
            ["FILE_GET_AT", "2021-07-01T12:30:00", "Copy.txt"],
        ],
        [
            "uploaded at First.txt",
            "uploaded at Second.txt",
            "copied at Second.txt to Copy.txt",
            "rollback to 2021-07-01T12:10:00",
            "found at [Second.txt, First.txt]",
            "file not found",
        ],
    ),
}


def load_solution(path):
    spec = importlib.util.spec_from_file_location("practice_solution", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python check.py LEVEL FILE")

    level = int(sys.argv[1])
    path = Path(sys.argv[2])
    solution = load_solution(path)
    simulate = solution.simulate_coding_framework
    rollback_mode = getattr(solution, "ROLLBACK_RESTORE", None)

    for case_level in range(1, level + 1):
        operations, expected = CASES[case_level]
        if rollback_mode is None:
            actual = simulate(operations)
        else:
            actual = simulate(operations, rollback_mode=rollback_mode)

        if actual != expected:
            print(f"Level {case_level}: FAIL")
            print("expected:", expected)
            print("actual:  ", actual)
            return 1

        print(f"Level {case_level}: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
