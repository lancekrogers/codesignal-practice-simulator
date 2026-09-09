# Web UI source

The browser bundle is built from this directory by `../build.mjs`. Source files
and generated assets are intentionally separate: generated files belong in
`../src/codesignal_practice_simulator/web/static/` and are the only browser
runtime input shipped in the Python package.

This workspace contains only first-party browser source and public package
inputs.
