# ── Timed practice ─────────────────────────────────────────────────────────
# A run mirrors the real assessment: 90 minutes, levels in order, partial
# credit for every level you finish.

# Install the local simulator. Fetching the untracked assessment is a separate,
# explicit step because upstream material is FETCH_ONLY.
setup:
    {{python}} -m pip install -e {{justfile_directory()}}

# Fetch the seven pinned assessment files into the ignored fixture cache.
fetch:
    {{python}} {{scripts}}/fetch_fixture.py --manifest {{justfile_directory()}}/docs/migration-manifest.json

# Start a new timed attempt (90 minutes by default)
practice minutes="90":
    @{{python}} {{scripts}}/new_attempt.py --minutes {{minutes}}

# Score every level of the current attempt
score:
    @-{{python}} {{scripts}}/scorecard.py

# Score a single level of the current attempt
level n:
    @-{{python}} {{scripts}}/scorecard.py --level {{n}}

# Full unittest output for one level (use when `just level n` says FAIL)
debug n:
    #!/usr/bin/env bash
    set -euo pipefail
    dir="$({{python}} {{scripts}}/scorecard.py --print-dir)"
    cd "$dir"
    # A failing test is the point of this recipe; don't add a just error banner.
    {{python}} -m unittest -v test_simulation.TestSimulateCodingFramework.test_group_{{n}} || true

# Time remaining in the current attempt
time:
    @{{python}} {{scripts}}/scorecard.py --time-only

# Stop the clock: score, then write RESULT.md into the attempt
submit:
    @-{{python}} {{scripts}}/scorecard.py --submit

# Print the current attempt directory
where:
    @{{python}} {{scripts}}/scorecard.py --print-dir

# Read a level's task description
task n="1":
    @cat {{assessment}}/level{{n}}.md

# List past attempts, newest first
attempts:
    #!/usr/bin/env bash
    set -euo pipefail
    found=0
    for name in $(ls -1 attempts 2>/dev/null | sort -r); do
        dir="attempts/$name"
        [ -d "$dir" ] || continue
        found=1
        if [ -f "$dir/RESULT.md" ]; then
            score="$(sed -n 's/^- Levels passed: //p' "$dir/RESULT.md" | head -1)"
            printf '  %-34s %s\n' "$name" "$score"
        else
            printf '  %-34s (unsubmitted)\n' "$name"
        fi
    done
    [ "$found" = 1 ] || echo "  no attempts yet — run 'just practice'"
