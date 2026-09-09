# CodeSignal Practice Simulator
#
# `just fetch` retrieves the pinned assessment into the ignored cache.
# `just practice` starts a timed run against that untouched cache.

import 'justfiles/practice.just'
import 'justfiles/verify.just'

python := 'python3'
scripts := justfile_directory() / 'scripts'
solution := justfile_directory() / 'solution'
assessment := justfile_directory() / '.cache' / 'codesignal-fixtures' / '6aab304' / 'assessment' / 'file_storage'
simulator := justfile_directory() / '.venv' / 'bin' / 'codesignal-sim'

# List available recipes
@default:
    just --list --unsorted
