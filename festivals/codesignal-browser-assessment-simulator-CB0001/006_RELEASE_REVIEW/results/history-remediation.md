# B15 candidate-history remediation

## Scope and design boundary

Implemented the narrow CB0001 B15 correction in the candidate-document owner,
its lifecycle/support tests, the focused candidate browser journey, and D002.
Status checks showed concurrent scoring-service, scoring-test, and web-server
evaluation-test edits. They were not read, edited, or reverted.

History reconstruction now sorts records by descending durable
`operation_order`, initializes `next_hash` from the current ETag, and visits
each record once. A record is accepted only when its `new_hash` matches
`next_hash`; the traversal then advances to `prior_hash`. Matching no-op
records advance the chain but are omitted from published history. Repeated
hashes are not collapsed, and at most 50 content-changing operations are
published. Durable order gaps remain legal.

No CAS, schema, attempt lock, candidate ownership, symlink, lifecycle finality,
snapshot-before-source, or pruning boundary changed. D002 now says 50
content-changing operations rather than 50 distinct predecessors and documents
ordered traversal, no-op omission, repeated hashes, and orphan handling.

## Causal regression and verification commands

All commands used synthetic fixture workspaces. No real candidate, cache,
reference, study, solution, vendor, capability value, raw source, screenshot,
trace, build, install, fetch, full browser suite, commit, push, or festival
state mutation was used.

| Command | Result |
| --- | --- |
| `python3 -m unittest tests.test_candidate_document_lifecycle.CandidateDocumentLifecycleTests.test_repeated_content_and_noop_keep_oldest_predecessor_restorable tests.test_candidate_document_lifecycle.CandidateDocumentLifecycleTests.test_frozen_clock_retains_50_changes_across_pruned_noop_order_gaps tests.test_candidate_document_lifecycle.CandidateDocumentLifecycleTests.test_unpublished_orphan_is_omitted_then_pruned_after_retry` | Before the implementation change: **3 run, 2 failed, 1 passed**. Repeated/no-op history exposed only one predecessor; frozen-clock retention exposed only operation 110 instead of 50 changing operations. The failed-cleanup orphan regression already passed. |
| Same three-test command after the implementation change | **3 passed** in 0.376 seconds. |
| `python3 -m unittest tests.test_candidate_document_models tests.test_candidate_document_core tests.test_candidate_document_lifecycle tests.test_candidate_document_safety` | **26 passed** in 0.662 seconds. This includes existing CAS, locking, schema, ownership, symlink, finality, snapshot-before-source, published-but-error, and safety coverage plus the new repeated/no-op, 50-change retention, and failed-cleanup retry/prune cases. |
| Same 26-test candidate-document command after final assertion cleanup | **26 passed** in 0.644 seconds. |
| `cd webui && ./node_modules/.bin/playwright test tests/candidate_journey.spec.mjs` | **6 passed** in 12.707 seconds with locked Chromium and the default failure/privacy/success reporters. The added journey creates a synthetic C0-C1-C2-C1-no-op sequence through the local API, reconnects, restores the oldest predecessor through the History UI, and verifies persisted current content and ETag through the API. |
| `git diff --check` | Passed after implementation; no whitespace errors. |

## Result

The B15 cycle-break cause is removed without widening service ownership or
transport behavior. Unpublished orphan records are omitted, a same-content
retry is published at its later durable order, successful pruning removes the
orphan, published-but-error recovery remains visible, and repeated content no
longer hides the oldest recoverable predecessor.

This is focused remediation evidence only. The coordinator owns cumulative
verification, independent review, commit/push, festival state, and release.
