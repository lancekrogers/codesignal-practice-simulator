# ── Post-attempt study and compatibility ────────────────────────────────────

# Bundled assessment tests (levels 1-4) from the ignored fixture cache against
# the reference solution. This is compatibility verification, not timed play.
test-compat:
    cd {{solution}} && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="{{solution}}:{{assessment}}" {{python}} -m unittest -v test_simulation

# Spec-accurate tests: real rollback, TTL boundaries, error cases
study-spec:
    cd {{solution}} && {{python}} -m unittest -v test_spec

# Simple cumulative solutions, one program per assessment level
study-stages:
    cd {{solution}} && {{python}} -m unittest -v test_stages

# Every compatibility, reference, and staged suite
test-all: test-compat study-spec study-stages

# Check a local post-attempt study file against one staged checker.
study-check level file:
    cd {{justfile_directory()}}/study && {{python}} check.py {{level}} {{file}}

# Remove Python caches
clean:
    find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache
