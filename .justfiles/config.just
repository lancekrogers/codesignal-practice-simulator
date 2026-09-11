# Shared absolute paths also work when a module is invoked directly.
root := source_directory() / '..'
python := env_var_or_default('PYTHON', 'python3')
workspace := env_var_or_default('SIMULATOR_WORKSPACE', root)
simulator := root / '.venv' / 'bin' / 'codesignal-sim'
solution := root / 'solution'
assessment := root / '.cache' / 'codesignal-fixtures' / '6aab304' / 'assessment' / 'file_storage'
