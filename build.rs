/// Build script for vibecoded_yukkuri_game.
///
/// On Windows with a uv-managed Python interpreter, `python313.dll` lives
/// inside the uv CPython install directory rather than in a system location
/// that the Windows DLL loader searches automatically.  This script:
///
/// 1. Resolves the Python prefix from the `PYO3_PYTHON` environment variable
///    (already set via `.cargo/config.toml`).
/// 2. Emits `cargo:rustc-link-search=native=<python_dir>` so the linker
///    records the DLL directory in the binary's DLL search path (Windows PE
///    RPATH equivalent via `/LIBPATH`).
/// 3. Emits `cargo:rerun-if-env-changed` directives so the script is rerun
///    when the Python interpreter path changes.
fn main() {
    println!("cargo:rerun-if-env-changed=PYO3_PYTHON");
    println!("cargo:rerun-if-env-changed=VIRTUAL_ENV");

    // Only needed on Windows — Unix embeds RPATH in ELF directly via pyo3-build-config.
    #[cfg(target_os = "windows")]
    emit_windows_python_link_search();
}

#[cfg(target_os = "windows")]
fn emit_windows_python_link_search() {
    use std::path::Path;
    use std::process::Command;

    // Prefer the interpreter pointed to by PYO3_PYTHON; fall back to `python`.
    let python = std::env::var("PYO3_PYTHON").unwrap_or_else(|_| "python".to_string());

    // Ask Python for its prefix (the directory that contains python313.dll).
    let output = Command::new(&python)
        .args(["-c", "import sys; print(sys.prefix)"])
        .output();

    match output {
        Ok(out) if out.status.success() => {
            let prefix = String::from_utf8_lossy(&out.stdout).trim().to_string();
            let dll_dir = Path::new(&prefix);

            // Emit a native link-search path so the Windows linker writes the
            // directory into the binary's DLL load path.
            println!("cargo:rustc-link-search=native={}", dll_dir.display());

            // Also search the Scripts subdirectory (contains python3.dll shim).
            let scripts = dll_dir.join("Scripts");
            if scripts.exists() {
                println!("cargo:rustc-link-search=native={}", scripts.display());
            }
        }
        Ok(out) => {
            eprintln!(
                "build.rs: python prefix query failed (exit {:?}): {}",
                out.status.code(),
                String::from_utf8_lossy(&out.stderr)
            );
        }
        Err(e) => {
            eprintln!(
                "build.rs: could not invoke '{}' to determine Python prefix: {}",
                python, e
            );
        }
    }
}
