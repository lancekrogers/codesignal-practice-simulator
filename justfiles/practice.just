# ── Timed simulator ─────────────────────────────────────────────────────────
# These recipes use the versioned `codesignal-sim` attempt/session layout.

# Install the local simulator. FETCH_ONLY material is fetched separately.
setup:
    {{python}} -m venv {{justfile_directory()}}/.venv
    {{justfile_directory()}}/.venv/bin/python -m pip install -e {{justfile_directory()}}

# Fetch the seven pinned assessment files into the ignored fixture cache.
fetch:
    {{simulator}} fetch --workspace-root {{justfile_directory()}}

# Start a new 90-minute attempt with a UUID directory and session.json.
practice:
    {{simulator}} start --workspace-root {{justfile_directory()}}

# Start a drill with an explicit persisted duration.
practice-drill seconds="1800":
    {{simulator}} start --workspace-root {{justfile_directory()}} --mode drill --drill-duration-seconds {{seconds}}

# Resume the selected active attempt.
resume:
    {{simulator}} resume --workspace-root {{justfile_directory()}}

# Show the selected attempt's derived status and remaining time.
status:
    {{simulator}} status --workspace-root {{justfile_directory()}}

time:
    {{simulator}} time --workspace-root {{justfile_directory()}}

# Score all copied candidate test groups; only this recipe returns exit 5 for non-passing groups.
test:
    {{simulator}} test --workspace-root {{justfile_directory()}}

# Finalize the selected attempt once; a repeat returns its stored result.
submit:
    {{simulator}} submit --workspace-root {{justfile_directory()}}

# Read safe, non-authoritative attempt context without candidate source.
context:
    {{simulator}} context --workspace-root {{justfile_directory()}}

# Read only the copied prompt from the selected attempt.
task n="1":
    {{simulator}} task --workspace-root {{justfile_directory()}} --level {{n}}

# List UUID attempt directories. active.json selects the current one.
attempts:
    #!/usr/bin/env bash
    set -euo pipefail
    for dir in attempts/*; do
        [ -d "$dir" ] && [ ! -L "$dir" ] && basename "$dir"
    done
