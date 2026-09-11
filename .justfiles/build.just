import 'config.just'
set working-directory := '..'

[private]
default:
    @just --justfile '{{root}}/justfile' --unsorted --list build

# Install the exact locked frontend toolchain (development only).
deps:
    npm --prefix webui ci --ignore-scripts --no-audit --no-fund

# Rebuild bundled browser assets; refresh the browser afterward.
assets:
    npm --prefix webui run build

# Validate bundled asset integrity.
assets-check:
    '{{python}}' scripts/check_assets.py
