# 003.02.01 — Transfer Teaching, Reference, and Compatibility Assets

## Transfer record

The transfer program selected exactly the 24 manifest records with
`decision: include`. Before copying each record, it verified that the source
was a regular, non-symlink file and that its SHA-256 matched
`docs/migration-manifest.json`. Each selected record was classified
`user_authored`, had a non-null destination, and had no cache path. No
null-mapped or vendor record was copied from SOURCE.

| # | SOURCE path | Destination | Verified SHA-256 |
| --- | --- | --- | --- |
| 1 | `README.md` | `docs/legacy/explore-README.md` | `92685854d2cb1c14289da04ff2242ce2210c54fa7d2ad5f82f5eceb2f7057c97` |
| 2 | `justfile` | `justfile` | `71aecd7d7ca40eea6fb0cd32b8b3028b6f2d4330e6344a3a27d2d495139a5c8b` |
| 3 | `justfiles/practice.just` | `justfiles/practice.just` | `3f7ed51ec3081a88e8ecdbda2c11feb8d47223be1f834725b759d1c933a5401d` |
| 4 | `justfiles/verify.just` | `justfiles/verify.just` | `b19405695da070b03baa3e824333f9e7bd1f379517cf2909a655a2e82abd8b3a` |
| 5 | `notes/level4-rollback-discrepancy.md` | `notes/level4-rollback-discrepancy.md` | `beb7651fe30251a0e5f36b7790d1a3911ecbaea11d77b3bde6b6ddfc3b1d599a` |
| 6 | `notes/walkthrough.md` | `notes/walkthrough.md` | `50ca68b1e721981f5c485a4b130269252f977df598875a593d346827cac3de50` |
| 7 | `scripts/new_attempt.py` | `scripts/new_attempt.py` | `dfd71c93dd0c391f24b7a04ef9cff302e70c5bed224ea343ac87c91dbe6e765c` |
| 8 | `scripts/scorecard.py` | `scripts/scorecard.py` | `db313d4725b3eaff3182e10ea70554da2b036be76e0d4c7d84358036e0e6c086` |
| 9 | `solution/simulation.py` | `solution/simulation.py` | `d9a1b242a68336a0435ee9a67a9df8bc3db513b22f920a8193dd0220ed4d4598` |
| 10 | `solution/stages/README.md` | `solution/stages/README.md` | `822df0c1454301f7da0eddc4185f88a1993ddf5e909a93d883588a662b40a808` |
| 11 | `solution/stages/__init__.py` | `solution/stages/__init__.py` | `5323b8da247ff04d56a853fd7cb6f33534204c8df8f04a9f905851b49f998b89` |
| 12 | `solution/stages/level1.py` | `solution/stages/level1.py` | `700fd5286f1a4393cceaaa2697a84052d0063178f88cc724687d1582067365e8` |
| 13 | `solution/stages/level2.py` | `solution/stages/level2.py` | `b295aaf430c50eb08d1879ac7c1b005b1b65553b11388e7653cfbfe63e96704f` |
| 14 | `solution/stages/level3.py` | `solution/stages/level3.py` | `071e408c27f5ea14a47e0f91aea0487aa195e9877f802f701c43f2326a6f0f80` |
| 15 | `solution/stages/level4.py` | `solution/stages/level4.py` | `04f09733b5b38c96910097fa825d8bac9b97f0fa66c6661a7bfdc14e81117503` |
| 16 | `solution/test_spec.py` | `solution/test_spec.py` | `7262aa564ee064a84814fe6db64ba0179609d465bcca552ee728aa0bafd58567` |
| 17 | `solution/test_stages.py` | `solution/test_stages.py` | `20ada07da5e902fbd9a908a504f0dea2ec2a77e4101030c86f17af2bd7af865c` |
| 18 | `study/README.md` | `study/README.md` | `b6ee9f75fa129a07090177250e95110c306c9ae832c9bffd48406e9c520e8d04` |
| 19 | `study/check.py` | `study/check.py` | `eb4303f1446d1c79ceb6e68d988c671e8b872fd327f2de6769a728792861d8d3` |
| 20 | `study/level1.py` | `study/level1.py` | `42d7decbade24a9a5e13820ca4cd73dc67e5c610511679ed8a5b354ebd4576ec` |
| 21 | `study/level2.py` | `study/level2.py` | `9f17d27193c6a0e56c21bc35ba74531dd1f7ea613e4c83542d46a0af773824d5` |
| 22 | `study/level3.py` | `study/level3.py` | `0e72bccb5254bc784fcb96e63b550a697e72ab41e3c600cc1296f517f19fb8e7` |
| 23 | `study/level4.py` | `study/level4.py` | `a111107ae319f1c27505dabc6fcc5f5b7195dc0d7dcf2648fdd0990bf4060eeb` |
| 24 | `study/starter.py` | `study/starter.py` | `f33f5362ff0db98ab5ee906a497608220c8026254c0cbcfdfa6b26e32fdab407` |

The source root README is preserved as the declared legacy document. The
product-root README was then written for learners and is not a vendor copy.

## Adaptations

- `README.md` now separates local setup from the explicit FETCH_ONLY fetch,
  describes the ignored pinned cache, directs learners through a timed
  simulator followed by staged solutions, and documents the level-4
  compatibility-versus-specification distinction.
- `scripts/new_attempt.py` now reads the assessment only from the declared
  ignored cache and reports a clear fetch instruction when it is incomplete.
- `justfile` and the two user-authored Just fragments now use the cache path,
  provide separate `setup` and `fetch` recipes, avoid upstream requirements,
  and run the fetched bundled test without writing bytecode into the cache.
- `study/check.py` registers dynamic modules before execution for Python 3.14
  compatibility and passes `ROLLBACK_RESTORE` when a checked reference exposes
  that explicit spec mode. The simple staged examples were not changed.

The bundled level-4 test requires announce-only rollback compatibility;
`test-spec` and the study checker require state-restoring rollback as the
level-4 prose specifies. Both modes pass their appropriate checks.

## Commands and results

All commands were run from
`/workspace/campaign/projects/codesignal-practice-simulator`
unless noted otherwise.

| Command | Exit | Result |
| --- | --- | --- |
| Python transfer program selecting manifest `decision == "include"` records, hashing each source before `shutil.copyfile` | 0 | Copied exactly 24 approved mappings; every listed source digest matched. |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked` | 0 | PASS |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache` | 0 | PASS; all and only seven declared cached files had the manifest hashes. |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary` | 0 | PASS |
| `PYTHONDONTWRITEBYTECODE=1 just test-all` | 0 | Bundled compatibility suite: 4 passed; spec suite: 26 passed; staged suite: 12 passed. |
| `PYTHONDONTWRITEBYTECODE=1 python3 study/check.py 4 solution/simulation.py` | 0 | Levels 1 through 4: PASS. |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests/test_migration.py` | 0 | 12 fixture-contract and boundary tests passed. |
| `git diff --cached --check` | 0 | PASS |
| `.githooks/pre-commit` | 0 | Git-boundary verification passed. |
| `.githooks/pre-push` | 0 | Git-boundary verification passed. |

An initial bundled-test command created an ignored `__pycache__` file in the
fixture tree. It was immediately removed, the empty directory was removed,
and the final fixture-cache verification above passed. No fetcher was run
against the existing project cache; its seven declared files were verified in
place.

## Commit and push

The 25 intended project paths (the 24 declared destinations plus the
learner-facing root README) were committed with `fest commit` and pushed to
`origin/main`. The pre-push Git-boundary hook passed, the worktree is clean,
and campaign integration was not touched.

transfer_commit_sha: 39568f2577b79f715473d73a9306bfc7d57eb0a4
transfer_remote_main_sha: 39568f2577b79f715473d73a9306bfc7d57eb0a4
transfer_remote_equality: PASS
