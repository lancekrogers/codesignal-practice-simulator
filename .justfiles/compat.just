# Hidden compatibility shortcuts; implementations live in named modules.
[private]
practice: app::practice
[private]
practice-drill seconds='1800': (app::drill seconds)
[private]
resume: app::resume
[private]
status: app::status
[private]
time: app::time
[private]
test: app::test
[private]
submit: app::submit
[private]
context: app::context
[private]
task n='1': (app::task n)
[private]
attempts: app::attempts
[private]
test-compat: study::compat
[private]
study-spec: study::spec
[private]
study-stages: study::stages
[private]
test-all: study::all
[private]
study-check level file: (study::check level file)

# Legacy cleanup, limited to generated Python caches (not attempts or fixtures).
[private]
clean:
    find src tests scripts solution study -type d -name __pycache__ -prune -exec rm -rf {} +
    rm -rf .pytest_cache
