# run_test.ps1 — Cargo test runner for Windows with uv-managed Python.
#
# This script is invoked by cargo as the [target.runner] when running tests or
# `cargo run` on Windows.  It prepends the uv CPython install directory to PATH
# so that python313.dll is found by the Windows DLL loader before the test
# binary is launched.
#
# Usage (automatic via .cargo/config.toml — do not call directly):
#   cargo test --test migration_test
#
# The uv CPython directory is read from the PYTHON_DLL_DIR environment variable
# if set, or defaults to the path baked in below.  Override it in your shell if
# you have a different Python version or install location:
#   $env:PYTHON_DLL_DIR = "C:\path\to\cpython-X.Y.Z-windows-x86_64-none"

param(
    [Parameter(Mandatory, Position = 0)]
    [string]$Executable,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Args
)

$PythonDllDir = $env:PYTHON_DLL_DIR
if (-not $PythonDllDir) {
    $PythonDllDir = "C:\Users\gamin\AppData\Roaming\uv\python\cpython-3.13.5-windows-x86_64-none"
}

$env:PATH = "$PythonDllDir;$env:PATH"

& $Executable @Args
exit $LASTEXITCODE
