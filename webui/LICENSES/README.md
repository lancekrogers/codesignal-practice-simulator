# Third-party notices

The files named by `runtime-notices.json` are byte-for-byte copies from the
locked installed packages. The runtime notice boundary starts at
`monaco-editor` and follows its non-optional lockfile dependencies, currently
`dompurify` and `marked`.

- `monaco-editor.MIT.txt` and `monaco-editor.ThirdPartyNotices.txt` — Monaco
- `dompurify.Apache-2.0.txt` and `dompurify.MPL-2.0.txt` — DOMPurify
- `marked.MIT.txt` — marked

The esbuild and Playwright files are retained for source/test-tooling
attribution only and are intentionally excluded from the packaged runtime
`NOTICE.txt`.
