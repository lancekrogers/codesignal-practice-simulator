# Web UI provenance

This workspace is the reproducible input boundary for the offline browser
bundle. Node is needed only to install and build these inputs; the Python
package serves generated static files and does not require Node at runtime.

## Direct npm inputs

The exact versions below are declared in `package.json` and resolved in the
npm lockfile. Registry tarballs and repository metadata are recorded together
so the source of every direct input is auditable.

| Package | Version | Registry tarball | Repository | Integrity |
| --- | --- | --- | --- | --- |
| `monaco-editor` | `0.56.0` | `https://registry.npmjs.org/monaco-editor/-/monaco-editor-0.56.0.tgz` | `git+https://github.com/microsoft/monaco-editor.git` | `sha512-sXboRm3BeBeLm938eaiyLMe0OxzfXIlZvbv4ir/jVgQy1zDhWjgmny0WoN45fuDKhCCQsYMbBJrv/A6jd8aCUg==` |
| `esbuild` | `0.28.2` | `https://registry.npmjs.org/esbuild/-/esbuild-0.28.2.tgz` | `git+https://github.com/evanw/esbuild.git` | `sha512-HKVLS8dvII+xoKW9kmqxbRKrnWEXfJJr/FZhhJmiqIB0e053QNYFqOBouTMO/k5sID4MvCiUCvv8b9M4h32wIA==` |
| `@playwright/test` | `1.63.0` | `https://registry.npmjs.org/@playwright/test/-/test-1.63.0.tgz` | `git+https://github.com/microsoft/playwright.git` | `sha512-oxMK4vllB9RK5NQ2l1pq1IfOf2AvnEuj/vYGDj0H2nMtmtZpKtCwt/l00GEO6xjGfpBNAvjovvYdCm50dRQkpQ==` |

`package-lock.json` uses lockfile version 3 and records the exact versions,
resolved registry URLs, integrity hashes, licenses, and platform-specific
optional packages for the complete transitive graph. `npm ci --ignore-scripts`
is the reproducible installation command.

## Licenses

The browser bundle contains Monaco editor code and its locked non-optional
runtime dependencies DOMPurify and marked. `LICENSES/runtime-notices.json`
defines that closure. The exact installed-package license and notice text is
copied into `LICENSES/` and assembled into the packaged `NOTICE.txt`.
esbuild and Playwright are build/test tooling and are not in the runtime
notice boundary.

## Build and output boundary

From this directory:

```sh
npm ci --ignore-scripts
npm run check
npm run build
```

`npm run build` invokes `node build.mjs`. The build may use temporary files
under `webui/.tmp/`, but its package output is written only to:

`src/codesignal_practice_simulator/web/static/`

That destination contains the manifest and browser assets served by the
Python package. Generated package assets are reviewable and trackable; local
installations, browser binaries, reports, test results, and temporary build
files remain ignored. No network request is made by the packaged application.

## Static scan allowlist

The package checker rejects absolute checkout or temporary paths, secrets and
tokens, `FETCH_ONLY`, cache/install paths, and external runtime URL targets.
The only URL literals retained in browser text are exact standards namespaces
and Monaco/VS Code diagnostic links emitted by Monaco, plus exact
Apache/Puppeteer links required by retained license notices. These allowlisted
strings are data or diagnostic text only: the checker separately rejects
`fetch`, `WebSocket`, `EventSource`, `sendBeacon`, `importScripts`, or
`new URL` calls whose literal target is external. Application requests are
relative same-origin paths.

Publication stages every file, including `manifest.json`, beside the live
directory and commits it with a lock-protected pair of atomic directory
renames. The sibling lock has an owner PID and bounded stale-owner recovery.
Transaction state is flushed to a temporary marker before rename; the next
build can recover prepared, old-moved, live-renamed, malformed, or interrupted
transactions without publishing an incomplete manifest.

Directory-backed Python resource reads use the same lock and re-resolve the
package root after waiting, so they observe one complete old or new
generation. Immutable installed wheels do not build at runtime and can read
without a writable publication lock.
