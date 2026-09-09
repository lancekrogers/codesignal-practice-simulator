# CodeSignal Practice Simulator

A local Python 3.10+ practice-simulator scaffold.

## Install

```sh
python3 -m pip install -e .
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
```

## Fixture policy

This project uses a **FETCH_ONLY** policy for upstream material. Upstream and
vendor files are never tracked in this repository. A later setup workflow
retrieves validated files into the ignored `.cache/codesignal-fixtures/` cache.
