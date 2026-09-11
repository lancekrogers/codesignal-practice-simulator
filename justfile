#!/usr/bin/env just --justfile
# Local browser assessment development and practice.

import '.justfiles/config.just'
import '.justfiles/compat.just'

[doc('Install, fetch, and manage timed CLI attempts')]
mod app '.justfiles/app.just'

[doc('Frontend dependencies and bundled assets')]
mod build '.justfiles/build.just'

[doc('Python, browser, packaging, and provenance checks')]
mod check '.justfiles/check.just'

[doc('Explicit post-attempt study and legacy compatibility')]
mod study '.justfiles/study.just'

[private]
default:
    @just --justfile '{{ root }}/justfile' --list --unsorted

# Install the editable Python app; fixture fetching stays explicit.
setup: (app::setup python)

# Fetch the pinned assessment into the selected workspace.
fetch: (app::fetch workspace)

# Launch the local web app and open the browser; accepts web CLI flags.
[continue]
[positional-arguments]
dev *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ ! -x '{{ simulator }}' ]]; then
        echo 'Simulator is not installed. Run just setup, then just fetch.' >&2
        exit 1
    fi
    exec '{{ simulator }}' web --workspace-root '{{ workspace }}' --port 0 "$@"

# Run the canonical project verification suite.
verify: (check::verify python)
