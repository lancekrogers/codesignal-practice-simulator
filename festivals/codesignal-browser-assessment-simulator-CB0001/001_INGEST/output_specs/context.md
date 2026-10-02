# Context and References

## Existing system

The private `codesignal-practice-simulator` repository already supplies a
durable Python 3.10+ simulator engine and CLI. Project commit `f1a178a` passed
158 tests, real-process console/module full/drill flows, exact isolated scorer
argv checks, seven-record FETCH_ONLY validation, and clean project/campaign
clone rehearsals.

Reusable anchors identified by repository review:

- `src/codesignal_practice_simulator/lifecycle.py`: `LifecycleService` owns
  start, resume, status/time, test transition, expiry, and submit lifecycle.
- `src/codesignal_practice_simulator/evaluation.py`: `EvaluationService` owns
  test and submission application behavior.
- `src/codesignal_practice_simulator/prompts.py`: `PromptService` performs
  locked, registry-validated reads of copied level prompts.
- `src/codesignal_practice_simulator/rendering.py`:
  `AttemptContextService` and derived status surfaces provide safe agent views.
- `src/codesignal_practice_simulator/workspace.py`: `WorkspaceManager` owns
  attempt creation, selection precedence, validation, and lock order.
- `src/codesignal_practice_simulator/persistence.py`: atomic state/event writes,
  locks, pointer handling, and submission recovery.
- `src/codesignal_practice_simulator/scoring.py`: exact attempt-local isolated
  scoring boundary.
- `src/codesignal_practice_simulator/cli.py`: transport-neutral
  `CommandApplication` protocol and the current private production composition
  root.
- Root and attempt `AGENTS.md`, `STATUS.md`, and `COACHING.md` define the
  operational terminal-agent boundary.

The missing core abstraction is a locked candidate-document/history service;
the web adapter must not access candidate paths directly.

## Current CodeSignal behavior used as interaction reference

Official candidate documentation says an assessment displays duration,
question count, instructions, and a practice option before starting; the
assessment then runs in one sitting with no pause. During the assessment the
countdown begins automatically, questions may be answered in any order, and
the IDE exposes language/settings plus Description, History, Rules, and Info
views. Submission is an explicit green action, with Skip/navigation available.

- https://support.codesignal.com/hc/en-us/articles/360045953873-Taking-an-assessment-on-CodeSignal

Official IDE documentation describes editor customization, autocomplete,
sample test cases, and a distinct submission run that may include hidden
tests. This simulator will reproduce the interaction distinction but will
label its own available scoring honestly.

- https://support.codesignal.com/hc/en-us/articles/360039872914-What-is-the-CodeSignal-Cloud-IDE-Coding-Environment

Official practice documentation confirms that practice content exists to
familiarize candidates with the assessment IDE. That candidate-familiarity
goal is the reason interaction fidelity is a first-class requirement here.

- https://support.codesignal.com/hc/en-us/articles/12984563824279-Practice-Content-Overview

## Decisions already established

- Local/offline browser application, not a hosted clone.
- Python/file-storage assessment only.
- Existing engine remains authoritative.
- No proprietary CodeSignal assets or fabricated hidden-test claims.
- Terminal coaching remains out-of-band from the candidate IDE and cannot
  silently influence scoring.

## Input processing audit

Both files present in `input_specs/` were read completely:

- `README.md` supplied the ingest procedure. Its four processing expectations
  are satisfied by `purpose.md`, `requirements.md`, `constraints.md`, and this
  context document.
- `seed.md` supplied the product request. Every requested behavior is traced to
  B01-B20 in `requirements.md`; the exclusions are traced to B21-B25 and the
  live-content/security constraints.

The seed's potentially ambiguous phrases were resolved as follows:

- “CodeSignal-like” means behavioral and spatial familiarity, not copied
  branding, assets, page source, or claims of official hidden tests.
- “Autocomplete” means locally bundled editor assistance; it does not require
  a language server or network service.
- “History” means candidate-source revisions, not lifecycle-event internals or
  keystroke surveillance.
- “Terminal agents must observe” means the existing derived `STATUS.md`,
  `COACHING.md`, context command, and attempt agent policy remain the supported
  boundary. It does not authorize silent candidate-code edits.
- “Offline” means no network after the project dependencies/assets have been
  installed or built; fixture acquisition retains the existing explicit fetch
  and hash-validation process.

No unresolved ambiguity changes the requested application shape or blocks
planning.
