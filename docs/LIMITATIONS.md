# Limitations

What SBV does **not** check, or checks only under assumptions. Each entry is
tagged *(scope)* for a deliberate decision or *(gap)* for a missing feature.

A validation compares summary and function only on a fixed set of
**observations**: the return value, the memory regions and files tagged in the
argspec, and the descriptors open at the end of the call. Anything else is
invisible, so a summary can be wrong about it and still pass.

- [What is observed](#what-is-observed)
- [File system](#file-system)
- [Engines](#engines)
- [Harness limits](#harness-limits)
- [Writing summaries: pitfalls](#writing-summaries-pitfalls)

---

## What is observed

### Memory: only argspec-tagged arguments *(scope)*

Only pointer arguments with `semantic: memory` are compared, byte by byte
(`mem_<name>_<i>`). `type: read` regions are included, so a summary writing to
read-only memory is caught. Both tests come from the same argspec, so both
sides always tag the same regions.

Not observed:

- arguments missing from the argspec (keeping it complete is the user's job);
- intermediate buffers and heap memory no argument reaches;
- globals, including `errno`;
- memory behind nested pointers (e.g. a struct field).

### Return values

Compared as `Ret`, except **pointers**: addresses differ between angr and the
loader, so they are recorded but not compared. Tag the memory instead.

### Unconstrained variables *(gap, partly addressed)*

A formula variable the sample does not bind is existentially quantified, so
the check almost always succeeds. Nothing verifies that every variable was
bound.

- **Memory:** safe if the argspec is complete.
- **Descriptors:** covered by the `file_open_fds` mask. A descriptor open on
  only one side is a mismatch (see
  [ARGSPEC.md — Open descriptors](ARGSPEC.md#open-descriptors)).
- **Harness truncation** (see [limits](#harness-limits)) leaves variables free
  silently.

---

## File system

| Limitation | Kind | Effect |
|---|---|---|
| No directories | gap | Flat sandbox; names exclude `/`, `.`, `..`. No `mkdir`, `opendir`, path resolution. |
| Closed descriptors are gone | scope | Only descriptors open at the end are compared; see the remark below. |
| File contents by name | gap | For `file: name` arguments only `file_<name>_exists` is compared, not contents or size. |
| Reopened files start empty | gap | `SymbolicFS` drops a file's contents when its last descriptor closes; POSIX keeps them. |
| File mode | gap | Symbolic side always uses `0644` unless the summary calls `__file_set_mode`. A function creating e.g. `0600` differs. |
| Open flags | gap | Summaries use fopen-style modes (`r`/`w`/`a`, `+`), i.e. six flag combinations. Others (`O_EXCL`, `O_CLOEXEC`, `O_WRONLY\|O_CREAT` without `O_TRUNC`, …) can't be matched. |
| `If` over several descriptors | gap | Only the return value is conditional; side effects of every branch are applied. Fine for `If(c, fd, -1)`, wrong between two valid fds. |

> **Remark: writes through closed descriptors are not checked.** A summary
> that writes the wrong bytes and then closes the file passes. This is outside
> the intended scope, where each summary models one libc function and only the
> summary of `close` itself closes a descriptor. It does affect functions that
> open, write and close internally, such as a `save_data`-style helper.

### Calls the harness does not intercept *(gap)*

The harness redirects `open`, `creat`, `openat`, `dup` and `dup2` (which
create descriptors) and `close` and `fclose` (which release them) to its own
wrappers at compile time, with `-D` macros. Because the redirection happens in
the source, it only catches calls written in the code being compiled. Calls
made from inside libc go straight to the real system call.

A descriptor the harness did not see is untracked. It is missing from
`file_open_fds`, and no `file_fd<N>_*` values are recorded for it, so its
offset, flags and contents are never compared. If the summary models that
descriptor as open, the two sides disagree and the sample is reported as
`mismatched`, even when the function is correct.

Descriptors are missed when they come from:

- **`fopen`, `fdopen` and `freopen`.** These call `open` from inside libc, so
  the wrapper never sees it. A function that `fopen`s a file and leaves it
  open always disagrees with a summary that models the open.
- **Other calls that create descriptors**, such as `fcntl(F_DUPFD)`, `pipe`,
  `socket` and `mkstemp`.

Two related gaps:

- **`rename` is not tracked.** The harness keeps the path each descriptor was
  opened with. After a `rename` that path is stale, and the file's contents
  are read back from the old name at the end of the test.
- **`creat` and `openat` are wrapped but untested.** For `openat` with a
  `dirfd` other than `AT_FDCWD`, the path is recorded relative to `dirfd`.

---

## Engines

- **`--engine se` cannot validate concrete file functions** *(scope)*. Only the
  summary's `__file_*` calls reach the `SymbolicFS`; the function's
  `open`/`read`/`write` hit angr's POSIX model, which doesn't know the test's
  files. The verdict is meaningless, so **use `--engine fuzz`**.
- **`passed` is not a proof** *(scope)*. It means no sample contradicted the
  summary; unreached behaviour is unchecked, and some tests (FILE\* ones in
  particular) get few samples. `mismatched` is a real counterexample.
- Samples build at `-m32` by default; both sides must share the architecture.
- Runs where the function calls `exit()` are discarded.
- FILE\* arguments come from `fdopen` (libc `malloc`). If a helper redirects
  `malloc` to `__mem_alloc`, closing the stream passes an arena pointer to
  glibc's `free()`.
- The harness provides only `__mem_alloc`; helpers calling `__mem_free`,
  `__n_allocd` or `__allocd` fail to link.

---

## Harness limits

The AFL++ harness uses fixed tables. Overflow is dropped or truncated silently,
which can leave variables unbound.

| Limit | Value | Beyond it |
|---|---|---|
| Tagged memory regions / test | 16 | not recorded |
| Bytes per tagged region | 4096 | truncated |
| Tagged file paths / test | 16 | not recorded |
| Tracked descriptors / test | 16 | untracked |
| File content read back | 4096 B | truncated |
| Path length | 63 chars | truncated |
| fd numbers in `file_open_fds` | 0–63 | ignored |
| `__mem_alloc` arena | 1 MiB | run discarded |

Absolute paths and paths containing `..` are never tagged.

---

## Writing summaries: pitfalls

**Don't assume failure away.** File names may be empty, so `__file_open` and
`__file_create` can fail. `__assume(_GE_(fd, 0))` drops those inputs and every
such sample becomes `mismatched`. Branch natively instead:

```c
int fd = __file_open(path, "w");
if (fd < 0)
    return -1;
```

**Counts must be concrete.** `fd`, `count`, `offset`, `size` and `mode` must be
concrete in file-API calls (`__file_write` raises `InvalidCountError`
otherwise). Fork on a symbolic length first:

```c
void fork_len(unsigned int n)
{
  if (n == 0)
    return;
  fork_len(n - 1);
}
```
