# Requirement extraction

## Purpose

Turn a single-assessment rehearsal into a reusable local practice product.
The user wants to choose exercises, repeat them, restart unfinished work, and
view previous submissions. They explicitly requested a festival, not a design
work item. This turn starts planning; it does not authorize deleting old work.

## Requirements

- Multiple selectable Python assessments, with original additional content as
  the proposed direction; exact count and tracks remain to be specified.
- Unlimited fresh attempts; confirmed abandon/restart preserves prior work.
- Discoverable history and read-only review of submitted source/results/timing.
- Existing-attempt compatibility, interrupted-operation recovery, and browser
  verification of select → practice → submit → review → retry.

## Constraints

Use the existing Python lifecycle/scorer and locally bundled UI. Keep the server
authoritative, offline-capable, and single-user. Do not inspect live candidate
source/history or protected assessment inputs. Test with synthetic workspaces.
Do not silently change the existing source-reset command into attempt restart.

## Initial context

Source audit at simulator commit 7833def shows scores and submission timestamps
are persisted. This is not an audit of any user's actual stored attempts.
The default registry contains only File Storage; browser start refuses a live
selected attempt. There is no abandoned state in SessionState and no history
listing route in the inspected router. Existing source history means versions
within an attempt, not a catalog of prior attempts.

## Decisions still needed

Specify content count/tracks, assessment version pinning, archive semantics,
restart failure recovery, exact source snapshot binding, and history pagination.
Recommended initial catalog: retain File Storage and add two original four-level
Python exercises (in-memory records and account ledger); this is a proposal,
not a claim that content has been approved or implemented.
