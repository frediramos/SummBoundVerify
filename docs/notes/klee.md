# Klee Notes

## Bugs

1. Could write to a file opened as read-only. (Test 11/13)

2. Could read from a file opened as write-only.

3. Never rejects a read-only file, even when it was opened as write-only.

4. `open` changes the file permissions (POSIX permissions, e.g. `0666`).

5. `dup` copies the file struct instead of sharing it, so the offset is not propagated.

## Notes

- KLEE cannot actually create files. All files are created when launching the tool based on the CLI options. An `open` just assigns an `fd` to a filename.

- KLEE's symbolic files only have `1` character. For instance, an `open` on a symbolic string "assumes" it be `a`.  

- There is a mismatch between concrete and symbolic files. File descriptors opened with a real `open` cannot be passed to KLEE summaries.
