# Assessment Provenance Draft

- upstream URL: https://github.com/PaulLockett/CodeSignal_Practice_Industry_Coding_Framework
- upstream commit: 6aab304 (6aab30450fc380a76ee631bbddff66a18853a8cf)
- GitHub `licenseInfo`: null
- `GET /repos/PaulLockett/CodeSignal_Practice_Industry_Coding_Framework/license?ref=6aab304`: HTTP 404 Not Found
license decision: FETCH_ONLY
- fixture cache root: `.cache/codesignal-fixtures/6aab304/`
- tracked vendor bytes: prohibited

The repository’s case-sensitive tree names its README `Readme.md`; the declared
fixture contract uses normalized fetch path `README.md` for the local
`vendor-readme.md` cache record. The `repository_path` field in the manifest
preserves the exact upstream spelling.

## Expected fetch paths and hashes

| Upstream path | Cache-relative path | SHA-256 |
| --- | --- | --- |
| `README.md` | `vendor-readme.md` | `b4c2fbb6810f5969b1cfaea9534369b7a1b1ba40fe759d9951804e727823eca5` |
| `practice_assessments/file_storage/level1.md` | `assessment/file_storage/level1.md` | `0529eb7272952842e50957a3823a063ad1f46c426d236c4f4cdaaba90a247a5b` |
| `practice_assessments/file_storage/level2.md` | `assessment/file_storage/level2.md` | `78a7c6f8fa4078b570af16399f158f30f91f5bc91e51c55171b4580c91f11695` |
| `practice_assessments/file_storage/level3.md` | `assessment/file_storage/level3.md` | `45218db3791433e8f089ef34c1c550205951e971300ca3ecfa08411f2caae7f0` |
| `practice_assessments/file_storage/level4.md` | `assessment/file_storage/level4.md` | `5e1f8bae5e82ea9a61cef9eaae512e9bc6df60a7473bd2ade1b20b1715c59736` |
| `practice_assessments/file_storage/simulation.py` | `assessment/file_storage/simulation.py` | `3f402921360fc7fc3deb30392425873844268ade3515fb74e0c909f30c809fdc` |
| `practice_assessments/file_storage/test_simulation.py` | `assessment/file_storage/test_simulation.py` | `3bc1451a1c10b5a77624e66a2dc32ea57e14446919b07378941e56fcbfcfa51a` |

Only these seven files may be fetched at runtime, atomically into the ignored
fixture cache. No upstream/vendor byte may be tracked or copied into PROJECT.

## Level 4 profiles

The fetched Level-4 compatibility profile is evaluated only from the copied
candidate source and copied bundled test. Its `ROLLBACK` expectation is
log-only, so it is useful for reproducing the fetched test behavior but is not
the prose specification. The prose-correct profile restores the file-storage
state at the requested time; it belongs to the original reference and
post-attempt study material, never to a live fetch-only scoring input.
