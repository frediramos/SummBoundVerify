# Limitations

What SBV does **not** check, or checks only under assumptions. Most of these
are deliberate scope decisions; a few are gaps in the current implementation.
Each entry says which.

A validation compares what the summary and the concrete function do to a
fixed set of **observations**: the return value, the memory regions and files
the argspec tags, and the file descriptors open at the end of the call.
Anything outside that set is invisible to both engines, so a summary can be
wrong about it and still pass.

- [What is observed](#what-is-observed)
- [File system](#file-system)
- [Engines](#engines)
- [Harness limits](#harness-limits)
- [Writing summaries: pitfalls](#writing-summaries-pitfalls)

---

## What is observed

### Memory: only argspec-tagged arguments *(scope)*

Memory is compared only for pointer arguments declared with
`semantic: memory` (and `type: write`) in the argspec. Each such region is
tagged with `__mem_addr` in both generated tests and lifted as
`mem_<name>_<i>`, one variable per byte.

Not observed:

- **Arguments missing from the argspec.** Configuring the argspec is the
  user's responsibility; an untagged argument is invisible to both sides, so a
  summary that writes to it wrongly (or writes to it when the function does
  not) passes.
- **Intermediate buffers**, and heap memory the function allocates that no
  argument reaches.
- **Globals**, including `errno`.
- **Memory behind nested pointers** — a struct field pointing elsewhere. Only
  the bytes of the tagged region itself are compared.

Because both tests are generated from the same argspec, the two sides always
tag the same regions: a region never ends up constrained on one side and
missing on the other (up to the [harness limits](#harness-limits)).

### Return values

The return value is compared as `Ret`, except when it is a **pointer**: an
address means nothing across runs (angr and the loader lay memory out
differently), so it is recorded but not compared. To check what a
pointer-returning function did, tag the memory it writes.

### Unconstrained variables *(gap, partly addressed)*

A formula variable the sample does not bind is existentially quantified by
the solver, so the check degenerates to "is there *some* value for it" —
almost always yes. The checker binds only what the sample records; it does
not verify that every non-auxiliary variable of the formula ended up bound.

- **Memory:** safe as long as the argspec is complete (see above).
- **File descriptors:** handled by `file_open_fds`, a bit mask of the open
  descriptors that both sides record. A descriptor open on only one side is a
  mismatch, instead of leaving its variables free (see
  [ARGSPEC.md — Open descriptors](ARGSPEC.md#open-descriptors)).
- There is no general safety net yet: a harness truncation (see
  [harness limits](#harness-limits)) leaves variables free silently.

---

## File system

### No directories *(gap)*

The file system is flat. There is no `mkdir`, `rmdir`, `opendir` or path
resolution, and the generated file names exclude `/` (and `.`/`..`), so every
file lives in a single sandbox directory. Functions that create or walk
directories cannot be validated.

### Closed descriptors are gone *(scope)*

A closed descriptor no longer exists, on both sides: its offset and flags are
not compared, and its number goes to the next `open`. Only descriptors still
open when the test ends are observed (`file_fd<N>_*` and `file_open_fds`).

Consequence: **what is written through a descriptor that is then closed is not
checked.** A summary that writes the wrong bytes and closes the file passes.
This is outside the intended scope — one summary per libc function, where only
the summary of `close` itself closes — but it does apply to functions that
open, write and close internally (a `save_data`-style helper).

### File contents by name are not compared *(gap)*

For `file: name` arguments the symbolic side lifts only whether the file
exists (`file_<name>_exists`), not its contents or size. The harness records
the bytes (`F` line), but there is nothing to compare them with. Contents are
compared only through descriptors that are open at the end.

### The symbolic model forgets closed files' contents *(gap)*

In the `SymbolicFS`, a file's contents live in the entries of its open
descriptors. When the last descriptor of a file is closed and the file is
reopened, the model starts it empty; POSIX keeps the bytes. This only matters
for a test that closes and reopens the same file.

### Modes and flags *(gap)*

- **Mode:** the symbolic side gives every file `0666 & ~022` (`0644`) unless
  the summary calls `__file_set_mode`. The harness sets `umask(022)` to match,
  but a concrete function that creates a file with another mode (e.g. `0600`)
  differs.
- **Flags:** a summary opens files with fopen-style strings (`r`, `w`, `a`,
  optionally `+`; `b`, `t`, `c`, `e` are ignored), which map to six flag
  combinations. The harness records the flags the concrete function passed to
  `open`. Any other combination — `O_WRONLY|O_CREAT` without `O_TRUNC`,
  `O_CLOEXEC`, `O_EXCL`, ... — cannot be matched by a summary.

### Calls the harness does not intercept *(gap)*

The harness tracks descriptors created by `open`, `creat`, `openat`, `dup`
and `dup2`, and released by `close` and `fclose` (redirected at compile time
with `-D`). Descriptors created any other way are invisible to it, and so are
missing from its `file_open_fds`:

- **`fopen`, `fdopen`, `freopen`**: the redirection is source-level, and these
  call `open` inside libc. A concrete function that `fopen`s a file and leaves
  it open disagrees with a summary that models the open.
- `fcntl(F_DUPFD)`, `pipe`, `socket`, `mkstemp`, ...

`creat` and `openat` are wrapped but not covered by any test. For `openat`
with a `dirfd` other than `AT_FDCWD` the path is recorded relative to `dirfd`.

`rename` is not tracked either: a descriptor's recorded path goes stale, and
its contents are then read from the old path.

### Descriptors with several possible values *(gap)*

When a file-API call receives a descriptor that is an `If` over several
values (from an `open` of a symbolic name), only its **return value** is made
conditional; the side effects of every branch are applied unconditionally.
This is correct for the usual `If(cond, fd, -1)` — the `-1` branch has no
effects — but not for an `If` between two valid descriptors, where both
receive the write.

---

## Engines

### `--engine se` cannot validate concrete file functions *(gap)*

Under symbolic execution only the summary's file API (`__file_*`) is routed
to the `SymbolicFS`. A concrete function's `open`/`read`/`write` go to angr's
own POSIX model, which knows nothing of the files the test set up: `read`
returns `-1`, buffers are left untouched, offsets never move. The resulting
verdict (typically `bug`) is meaningless. **Validate file functions with
`--engine fuzz`**, which runs the concrete function natively.

### Sampling cannot prove a summary correct *(by design)*

`passed` means no sampled input contradicted the summary. The fuzzer explores
by coverage of the concrete function, so behaviour it never reaches is never
checked, and some tests settle on few samples (FILE\* tests in particular).
A `mismatched` verdict is a real counterexample; a `passed` verdict is not a
proof.

### Other

- Samples are built at `-m32` by default to match the symbolic side's 32-bit
  types; both sides must use the same architecture.
- A concrete function that calls `exit()` has that run discarded.
- A FILE\* handed to the function comes from `fdopen`, which allocates through
  libc's `malloc`. If a helper library redirects `malloc` to `__mem_alloc`,
  closing that stream hands an arena pointer to glibc's `free()`.
- Of the heap API, the harness provides only `__mem_alloc`; a helper library
  that calls `__mem_free`, `__n_allocd` or `__allocd` fails to link.

---

## Harness limits

The AFL++ harness uses fixed-size tables. Exceeding them does not fail the
run — the excess is dropped or truncated, which can leave formula variables
unbound (see [Unconstrained variables](#unconstrained-variables-gap-partly-addressed)).

| Limit                                  | Value     | What happens beyond it          |
|----------------------------------------|-----------|---------------------------------|
| Tagged memory regions per test         | 16        | further regions are not recorded |
| Bytes per tagged region                | 4096      | the region is truncated          |
| Tagged file paths per test             | 16        | further paths are not recorded   |
| Tracked descriptors per test           | 16        | further descriptors are untracked |
| File content read back                 | 4096 B    | the content is truncated         |
| Path length                            | 63 chars  | the recorded path is truncated   |
| Descriptor numbers in `file_open_fds`  | 0–63      | higher numbers are ignored       |
| Allocation arena (`__mem_alloc`)       | 1 MiB     | the run is discarded             |

File names whose path is absolute or contains `..` are not tagged at all.

---

## Writing summaries: pitfalls

### Don't assume the failure case away

File names are symbolic and may be empty, so `__file_create` and
`__file_open` can fail. The pattern

```c
int fd = __file_open(path, "w");
if (__is_certain(_LT_(fd, 0)))
    return -1;
__assume(_GE_(fd, 0));      // drops every input where the open fails
```

removes the failure inputs from the summary's paths, and every sample with
such an input is reported as `mismatched`. Branch natively instead, so angr
keeps a path for each outcome:

```c
int fd = __file_open(path, "w");
if (fd < 0)
    return -1;
```

### Counts must be concrete

`fd`, `count`, `offset`, `size` and `mode` must be concrete in file-API calls
(`__file_write` raises `InvalidCountError` on a symbolic count). With a
symbolic length, fork on it natively first, so each path sees one value:

```c
void fork_len(unsigned int n)
{
  if (n == 0)
    return;
  fork_len(n - 1);
}
```
