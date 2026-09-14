import 'config.just'
set working-directory := '..'

[private]
default:
    @just --justfile '{{root}}/justfile' --unsorted --list check

# Canonical maintained verification (requires the fetched cache/build tools).
verify interpreter=python:
    '{{interpreter}}' scripts/run_legacy_checks.py
    '{{interpreter}}' -m unittest discover -s tests -v
    '{{interpreter}}' -m unittest tests.test_end_to_end -v
    git diff --check

# Maintained Python suite only.
unit:
    '{{python}}' -m unittest discover -s tests -v

# Bundled original exercises: allowlisted files, manifest hashes, runner entry points.
content:
    '{{python}}' scripts/check_content.py

# Frontend metadata, lockfile and licensing (not TypeScript checking).
frontend:
    npm --prefix webui run check

# Install the locked Chromium test browser (explicit network setup).
browser-install:
    npm --prefix webui run install:browser

# Run real synthetic browser journeys with the default privacy reporters.
[positional-arguments]
browser *args:
    npm --prefix webui run test:browser -- "$@"

# Verify offline installed-wheel browser behavior and archive boundaries.
wheel:
    '{{python}}' scripts/run_packaged_browser.py
