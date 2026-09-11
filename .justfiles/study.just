import 'config.just'
set working-directory := '..'

[private]
default:
    @just --justfile '{{root}}/justfile' --unsorted --list study

# Post-attempt first-party spec tests.
spec:
    cd '{{solution}}' && '{{python}}' -m unittest -v test_spec

# Post-attempt staged reference tests.
stages:
    cd '{{solution}}' && '{{python}}' -m unittest -v test_stages

# Deprecated post-attempt compatibility check against fetched upstream tests.
compat:
    cd '{{solution}}' && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='{{solution}}:{{assessment}}' '{{python}}' -m unittest -v test_simulation

# Deprecated aggregate; never part of timed candidate or dev startup.
all: compat spec stages

# Check a post-attempt study file against a staged checker.
check level file:
    cd '{{root}}/study' && '{{python}}' check.py '{{level}}' '{{file}}'
