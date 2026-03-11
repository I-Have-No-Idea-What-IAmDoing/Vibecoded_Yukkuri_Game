---
trigger: always_on
---

When running git commands that produce diff output (e.g., `git diff`, `git log -p`, `git show`), always pass `--no-color` to prevent ANSI escape codes from mangling the terminal output.

When running commands that may produce long lines (e.g., `git log`, `git show --stat`, `git diff`), pipe the output to a temp file and read it back with `view_file` instead of reading directly from the terminal. This avoids line-wrapping corruption in the pseudo-terminal. Example:
```
git diff --no-color > C:\Users\gamin\AppData\Local\Temp\git_output.txt
```
Then use `view_file` to read the temp file.
