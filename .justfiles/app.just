import 'config.just'
set working-directory := '..'

[private]
default:
    @just --justfile '{{root}}/justfile' --unsorted --list app

# Install the editable simulator without fetching assessment bytes.
setup interpreter=python:
    '{{interpreter}}' -m venv '{{root}}/.venv'
    '{{root}}/.venv/bin/python' -m pip install --no-deps -e '{{root}}'

# Fetch the seven pinned files into the ignored workspace cache.
fetch selected_workspace=workspace:
    '{{simulator}}' fetch --workspace-root '{{selected_workspace}}'

# Start a new 90-minute CLI attempt.
practice:
    '{{simulator}}' start --workspace-root '{{workspace}}'

# Start a drill with a persisted duration in seconds.
drill seconds='1800':
    '{{simulator}}' start --workspace-root '{{workspace}}' --mode drill --drill-duration-seconds '{{seconds}}'

# Resume the selected active attempt.
resume:
    '{{simulator}}' resume --workspace-root '{{workspace}}'

# Show derived status without candidate source.
status:
    '{{simulator}}' status --workspace-root '{{workspace}}'

# Show server-authoritative remaining time.
time:
    '{{simulator}}' time --workspace-root '{{workspace}}'

# Score the candidate; only this recipe returns exit 5 for non-passing groups.
test:
    '{{simulator}}' test --workspace-root '{{workspace}}'

# Finalize once; repeated submission returns the stored result.
submit:
    '{{simulator}}' submit --workspace-root '{{workspace}}'

# Read safe derived context, never candidate source.
context:
    '{{simulator}}' context --workspace-root '{{workspace}}'

# Read the selected attempt's copied prompt.
task n='1':
    '{{simulator}}' task --workspace-root '{{workspace}}' --level '{{n}}'

# List UUID attempt directories, excluding symlinks and active.json.
attempts:
    #!/usr/bin/env bash
    set -euo pipefail
    for attempt_dir in '{{workspace}}'/attempts/*; do
        if [[ -d "$attempt_dir" && ! -L "$attempt_dir" ]]; then
            basename "$attempt_dir"
        fi
    done
