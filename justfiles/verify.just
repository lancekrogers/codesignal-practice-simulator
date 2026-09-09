# ── Maintained verification and post-attempt compatibility ──────────────────

# Run the maintained simulator suite and reject whitespace errors.
verify:
    cd {{justfile_directory()}} && {{python}} -m unittest discover -s tests -v
    cd {{justfile_directory()}} && {{python}} -m unittest tests.test_end_to_end -v
    cd {{justfile_directory()}} && git diff --check HEAD

# Deprecated post-attempt compatibility check against the fetched bundled test.
# It is not a timed simulator command and requires the ignored fixture cache.
test-compat:
    cd {{solution}} && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="{{solution}}:{{assessment}}" {{python}} -m unittest -v test_simulation

# Post-attempt, spec-accurate reference tests: rollback, TTL, and error cases.
study-spec:
    cd {{solution}} && {{python}} -m unittest -v test_spec

# Post-attempt staged reference tests, one cumulative program per level.
study-stages:
    cd {{solution}} && {{python}} -m unittest -v test_stages

# Deprecated aggregate of post-attempt compatibility and study suites.
test-all: test-compat study-spec study-stages

# Check a local post-attempt study file against a staged checker.
study-check level file:
    cd {{justfile_directory()}}/study && {{python}} check.py {{level}} {{file}}

# Remove Python caches
clean:
    find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache
