# ── Reference solution ─────────────────────────────────────────────────────

# Bundled assessment tests (levels 1-4) from the ignored fixture cache against
# the reference solution. The cache must first be populated with `just fetch`.
test:
    cd {{solution}} && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="{{solution}}:{{assessment}}" {{python}} -m unittest -v test_simulation

# Spec-accurate tests: real rollback, TTL boundaries, error cases
test-spec:
    cd {{solution}} && {{python}} -m unittest -v test_spec

# Simple cumulative solutions, one program per assessment level
test-stages:
    cd {{solution}} && {{python}} -m unittest -v test_stages

# Every compatibility, reference, and staged suite
test-all: test test-spec test-stages

# Scorecard for the reference solution (expected: 4/4)
score-solution:
    @{{python}} {{scripts}}/scorecard.py --dir {{solution}}

# Diff your current attempt's simulation.py against the reference solution
compare:
    #!/usr/bin/env bash
    set -euo pipefail
    dir="$({{python}} {{scripts}}/scorecard.py --print-dir)"
    diff -u "{{solution}}/simulation.py" "$dir/simulation.py" || true

# Remove Python caches
clean:
    find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache
