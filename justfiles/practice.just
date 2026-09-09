# ── Timed simulator ─────────────────────────────────────────────────────────
# These recipes use the versioned `codesignal-sim` attempt/session layout.

# Install the local simulator. FETCH_ONLY material is fetched separately.
setup:
    {{python}} -m pip install -e {{justfile_directory()}}

# Fetch the seven pinned assessment files into the ignored fixture cache.
fetch:
    codesignal-sim fetch --workspace-root {{justfile_directory()}}

# Start a new 90-minute attempt with a UUID directory and session.json.
practice:
    codesignal-sim start --workspace-root {{justfile_directory()}}

# Start a drill with an explicit persisted duration.
practice-drill seconds="1800":
    codesignal-sim start --workspace-root {{justfile_directory()}} --mode drill --drill-duration-seconds {{seconds}}

# Resume the selected active attempt.
resume:
    codesignal-sim resume --workspace-root {{justfile_directory()}}

# Show the selected attempt's derived status and remaining time.
status:
    codesignal-sim status --workspace-root {{justfile_directory()}}

time:
    codesignal-sim time --workspace-root {{justfile_directory()}}

# Read only the copied prompt from the selected attempt.
task n="1":
    codesignal-sim task --workspace-root {{justfile_directory()}} --level {{n}}

# List UUID attempt directories. active.json selects the current one.
attempts:
    #!/usr/bin/env bash
    set -euo pipefail
    for dir in attempts/*; do
        [ -d "$dir" ] && [ ! -L "$dir" ] && basename "$dir"
    done
