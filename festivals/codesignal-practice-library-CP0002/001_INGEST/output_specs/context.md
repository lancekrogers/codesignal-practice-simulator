# Source audit and references

Audited 2026-09-11 against project commit 7833def. All anchors below are relative
to projects/codesignal-practice-simulator and were inspected in source. Recheck
anchors when implementation begins. No real attempt data was inspected.

| Finding | Evidence |
| --- | --- |
| Only File Storage is registered | src/codesignal_practice_simulator/assessments.py:56 defines it; :88 constructs the default registry with that definition alone. |
| Browser start rejects a live selection | src/codesignal_practice_simulator/lifecycle.py:92 passes a guard; :132 checks selected state and rejects active. |
| Fresh starts already use new identity/deadline | src/codesignal_practice_simulator/lifecycle.py:107 creates a UUID, start/deadline, and publishes an attempt. CLI start does not use the same live-selection guard as browser start; reconcile intentionally. |
| Submission persistence exists | src/codesignal_practice_simulator/lifecycle.py:240 returns stored results when already submitted; :262 persists score and submitted_at through the submission transition. |
| Session includes summary/time, not abandoned status | src/codesignal_practice_simulator/models.py:338 includes score, submitted_at and active/expired/submitted status. Schema-compatible abandonment must be designed. |
| Writes use the existing atomic persistence layer | src/codesignal_practice_simulator/persistence.py:86 reads validated sessions; :97 writes through atomic JSON under caller-owned locking. Reuse this boundary. |
| Bootstrap is single-assessment/selected-session oriented | src/codesignal_practice_simulator/application.py:174 resolves selected state and hardcodes file_storage at :185. |
| No attempt-list read route in inspected dispatch | src/codesignal_practice_simulator/web/routes.py:120 routes bootstrap and attempts; :177 requires POST for attempts. |
| Specific-attempt reads already exist | src/codesignal_practice_simulator/web/routes.py:208 uses attempt_id for session/time/source reads; it is not a past-attempt list. |
| Existing history is source versions | src/codesignal_practice_simulator/application.py:245 calls candidate_documents.list_history, not an assessment-submission catalog. |
| Browser starts from one bootstrap assessment | webui/src/app.ts:51 sends bootstrap.assessment.assessment_id; :97 reconnects bootstrap.session only. |

## What this establishes

The code supports durable submission summaries, and the UI/catalog needs
expansion. It does not establish that a particular user's submission exists,
that every historical detail is stored, or that current source is independently
bound to the exact scored revision. Those require further source/test design,
not unauthorized inspection of live candidate files.

## Prior work / integration

CB0001 is completed and explicitly excluded additional assessments:
festivals/.dungeon/completed/2026-09-10/codesignal-browser-assessment-simulator-CB0001/FESTIVAL_OVERVIEW.md.

Follow-ups addressed modular Just/dev, exit navigation/shutdown, and README/GIF.
The inspected local HEAD is the README PR #4 merge. Verify all required runtime
fixes are integrated before creating the implementation worktree; do not infer
every PR status from that commit alone.

Current local edits in README.md, docs/legacy/explore-README.md, and
tests/test_documentation.py are unrelated and preserved.
