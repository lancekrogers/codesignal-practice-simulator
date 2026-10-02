# Coordinator scope correction

Keep this remediation narrowly focused on the reported unexpected non-static
package-resource gap and prerequisite checks. Do **not** introduce a complete
sdist/wheel metadata catalog, a new TOML parser, or exact whole-archive membership
rules. The initial draft `_assert_sdist_metadata`, `_assert_wheel_metadata`,
`_distribution_metadata`, `_project_setting`, and metadata member constants should
be removed. They expand scope and are incompatible with existing sdist evidence:
setuptools normalizes the archive root with underscores, includes first-party
tests, and tar directory members need not end with a slash. Do not repair that
new catalog by accumulating special cases; retain the established archive logic.

The accepted correction is to reject non-static, non-Python members under the
actual runtime package prefix unless explicitly declared first-party resource
metadata (`resources/fixture-manifest.json`). Apply to wheel and sdist using the
existing static-prefix logic to resolve their prefixes. Test unexpected
`resources/fixture.json` and nested/other non-static resource names with synthetic
archives, alongside acceptance of known metadata, ordinary Python package files
and existing static members. Do not read protected fixture bytes. This is a
resource policy, not an assertion that future arbitrary Python source contents
are automatically safe. Existing source/provenance review remains required.

The prerequisite correction should remain small and make missing wheel
actionable. Shared module requirements/error formatting are reasonable; avoid
unnecessary interpreter-discovery redesign or new public abstractions solely
for mock-heavy tests. Preserve the existing configured/default/fallback order.

Run focused unit checks only, no real archive builds or browser runs while Sol
owns browser verification. Coordinator performs the real final builds afterward.
