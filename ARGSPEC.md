# Argspec — Argument Specification

An **argspec** is a YAML file that describes each function argument's semantic
role and test-generation constraints. It is the single source of truth for
how the tool should treat each argument during validation test generation.

## Quick Start

```yaml
# argspec.yaml for memcpy(void *dest, void *src, size_t n)
dest:
  type: void*
  semantic: memory
  memory:
    type: write
    size: 5

src:
  type: void*
  semantic: memory
  memory:
    type: read
    size: 5

n:
  type: size_t
  semantic: scalar
  scalar:
    maxvalue: 5
```

Pass it to the tool with `--argspec argspec.yaml` on the command line,
or add `argspec: argspec.yaml` to a `config.yaml` file.

## Schema

Each top-level key is the argument name as it appears in the C function
signature. The value is a mapping of properties. The key order **must** match
the argument order in the C function signature.

### Common Properties

| Property   | Description |
|------------|-------------|
| `type`     | The C type as a string (e.g. `int`, `char*`, `void*`). Optional; for documentation and cross-checking. |
| `semantic` | The argument's role: `scalar`, `memory`, or `file`. Defaults to `scalar`. |

Each semantic has its own configuration block described below.

---

### `semantic: scalar`

A plain value (integer, character, etc.). No tagging is emitted.

```yaml
n:
  type: size_t
  semantic: scalar
  scalar:
    maxvalue: 5
```

| `scalar` key | Type  | Description |
|------------|-------|-------------|
| `maxvalue` | `int` | Upper bound for this argument's symbolic value. |

---

### `semantic: memory`

A pointer to a memory region.

```yaml
dest:
  type: void*
  semantic: memory
  memory:
    type: write
    size: 5
```

| `memory` key | Values        | Default | Description |
|------------|---------------|---------|-------------|
| `type`     | `read`, `write` | `write` | Access mode. `read` = read-only, not tagged; `write` = read-write, tagged with `__mem_addr`. |
| `size`     | `int`         |         | Size of the symbolic array allocated for this argument. |

When any argument has `semantic: memory` with `memory.type: write`, the tool
automatically enables memory-side-effect evaluation.

---

### `semantic: file`

A file system argument. The `file` block describes how the file is passed
to the function and how it should be set up in the generated test.

```yaml
fildes:
  type: int
  semantic: file
  file:
    type: descriptor
    fname:
      symbolic: true
      size: 5
    data:
      symbolic: false
      size: 5
```

| `file` key | Values                          | Default      | Description |
|------------|--------------------------------|--------------|-------------|
| `type`     | `descriptor`, `pointer`, `name` | `descriptor` | How the file is passed to the function. |
| `fname`    | mapping                        |              | File name configuration. |
| `data`     | mapping                        |              | Initial file data configuration. |

**File types and their generated test setup:**

- **`descriptor`** — The function receives an `int fd`. The test creates a
  symbolic file name, calls `__file_create()` + `__file_open()`, optionally
  writes initial data with `__file_write()`, and passes the fd.

- **`pointer`** — The function receives a `FILE*`. Same setup as `descriptor`,
  but the fd is converted via `__FILE_from_fd(fd)` before the call.

- **`name`** — The function receives a `const char*` file path. The test
  creates a symbolic file name array and passes it directly. No open/write
  setup is generated.

**`fname` and `data` sub-blocks:**

| Key        | Type   | Description |
|------------|--------|-------------|
| `symbolic` | `bool` | Whether the value is symbolic (`true`) or concrete (`false`). |
| `size`     | `int`  | Size in bytes. |

---

### Generic Constraint Properties

These properties can appear on any argument regardless of its semantic type.
They control how the symbolic argument is constructed in the generated test.

| Property        | Type              | Description |
|-----------------|-------------------|-------------|
| `nullbytes`     | `int` or `[int]`  | Array index (or indexes) where null bytes are placed. |
| `default`       | `string`          | Default initialization value (e.g. `"NULL"`, `"&"`). |
| `concretearray` | `[int]` or `["N"]`| Concrete array indexes, or `["N"]` for N random concrete positions. |

The special default value `"&"` generates a reference: `foo(&arg, ...)`.

---

## Examples

### Simple scalar function

```yaml
# tolower(int c)
c:
  type: int
  semantic: scalar
```

### String function

```yaml
# strlen(const char *str)
str:
  type: char*
  semantic: memory
  memory:
    type: read
    size: 3
```

### Memory function with side effects

```yaml
# memcpy(void *dest, const void *src, size_t n)
dest:
  type: void*
  semantic: memory
  memory:
    type: write
    size: 5

src:
  type: void*
  semantic: memory
  memory:
    type: read
    size: 5

n:
  type: size_t
  semantic: scalar
  scalar:
    maxvalue: 5
```

### File descriptor function

```yaml
# read(int fd, void *buf, size_t count)
fd:
  type: int
  semantic: file
  file:
    type: descriptor
    fname:
      symbolic: true
      size: 5
    data:
      symbolic: true
      size: 10

buf:
  type: void*
  semantic: memory
  memory:
    type: write
    size: 10

count:
  type: size_t
  semantic: scalar
  scalar:
    maxvalue: 10
```

### FILE pointer function

```yaml
# fgets(char *s, int n, FILE *stream)
s:
  type: char*
  semantic: memory
  memory:
    type: write
    size: 10

n:
  type: int
  semantic: scalar
  scalar:
    maxvalue: 10

stream:
  type: FILE*
  semantic: file
  file:
    type: pointer
    fname:
      symbolic: true
      size: 5
    data:
      symbolic: true
      size: 20
```

---

## Test Generation Effects

This section describes how each argument semantic impacts the generation of
both **symbolic** (angr) and **concrete** (AFL++) validation tests.

### Generation Order

The test generator (`TestGen` in `validation_gen/test/base.py`) processes
arguments in a fixed order:

1. **File setup** — `_gen_file_setup()` for `descriptor`/`pointer` file args
2. **Symbolic args** — `SymbolicArgGen` for all remaining args
3. **Memory tagging** — `_tag_memory()` for `memory` args with `type: write`
4. **File tagging** — `_tag_files()` for `file` args with `type: name`
5. **Function call** + result recording

### Scalar — Generated Code

```c
size_t len = __sym_var_named("len", sizeof(size_t) * 8);
int max_1 = MAX_VALUE;
__assume(_ULE_(len, max_1));
```

- `ArgVisitor` detects a primitive type (no pointer/array indirection).
- `PrimitiveTypeGen` generates a symbolic variable declaration and an optional
  upper-bound constraint.
- **Symbolic (angr):** `len` becomes a `BVS` (bitvector symbol). The `_ULE_`
  constraint is added to the path condition.
- **Concrete (AFL++):** `__sym_var_named` reads bytes from the fuzzer's input
  tape. `__assume` discards the test run if the value exceeds the bound.

> **Important:** When a scalar is passed to a file API function (e.g.,
> `__file_read`, `__file_write`), its value **must be concrete** at call time.
> The symbolic FS only accepts concrete values for `fd`, `count`, and `offset`
> parameters. Only file *names* may be symbolic. If a function under test
> receives a symbolic count and passes it to a file operation, either use a
> fixed constant in the summary or call `__concretize()` before the file call.

### Memory — Generated Code

```c
// Array allocation + symbolic initialization
char buf[4];
for (int buf_idx_1 = 0; buf_idx_1 < 4; buf_idx_1++) {
    buf[buf_idx_1] = __sym_var_array("buf", buf_idx_1, sizeof(char) * 8);
}
buf[4 - 1] = '\0';

// Tagging (only for type: write)
__mem_addr("buf", buf, SIZE);
```

- `ArgVisitor` sees a `PtrDecl`, treats it as an array with the specified
  `size`.
- `ArrayTypeGen` generates a symbolic array where each element is drawn from
  `__sym_var_array`.
- For `type: write`, `_memory_args()` selects this argument for tagging:
  - **Symbolic:** `__mem_addr` registers the region. After the summary
    executes, `get_cnstr` reads the final memory contents and generates
    variables `mem_buf_0`, `mem_buf_1`, etc.
  - **Concrete:** `__mem_addr` records the address and size. After the
    function executes, `sbv_record` reads the final bytes and emits a record
    line `M buf 4 <hex>`.
- For `type: read`, the buffer is input data — its final state is not observed.

### File (`type: name`) — Generated Code

```c
// Symbolic path (standard array generation)
char path[5];
for (int path_idx_1 = 0; path_idx_1 < 5; path_idx_1++) {
    path[path_idx_1] = __sym_var_array("path", path_idx_1, sizeof(char) * 8);
}
path[5 - 1] = '\0';

// File tagging (before the function call)
__file_addr("path", path);
```

- The argument is generated as a normal symbolic array.
- `_tag_files()` emits `__file_addr("path", path)` to mark the path for
  post-call observation.
- **Symbolic:** The `file_addr` SimProcedure stores `("path", path)` in
  `ctx.FILE_TAGS`. After execution, `get_fs()` generates a constraint like
  `file_path_exists == 1` (or `0`).
- **Concrete:** `__file_addr` registers the path in `g_file_paths`. After the
  function returns, `sbv_record` checks whether the file exists on disk, reads
  its contents, and emits `F path <exists> <nbytes> <hex>`.
- **No file setup is performed.** The function itself decides what to do with
  the path.

### File (`type: descriptor`) — Generated Code

```c
// 1. Symbolic file name
char __fname_fd[5];
for (int __fname_fd_idx_1 = 0; __fname_fd_idx_1 < 5; __fname_fd_idx_1++) {
    __fname_fd[__fname_fd_idx_1] = __sym_var_array("__fname_fd", __fname_fd_idx_1, sizeof(char) * 8);
}
__fname_fd[5 - 1] = '\0';

// 2. Ensure filename is not empty
__assume(_NEQ_(__fname_fd[0], 0));

// 3. Create and open the file
__file_create(__fname_fd);
int fd = __file_open(__fname_fd, "w+");   // "w+" if data is specified, "w" otherwise

// 4. Optional: write initial data and reset offset
char __data_fd[5];
for (int __data_fd_idx_1 = 0; __data_fd_idx_1 < 5; __data_fd_idx_1++) {
    __data_fd[__data_fd_idx_1] = __sym_var_array("__data_fd", __data_fd_idx_1, sizeof(char) * 8);
}
__data_fd[5 - 1] = '\0';
__file_write(fd, __data_fd, 4);
__file_set_offset(fd, 0);
```

- `_gen_file_setup()` generates the entire file setup sequence.
- The argument name (`fd`) is added to the **skip set**, so `SymbolicArgGen`
  does not generate a `__sym_var_named("fd", ...)` for it — the value comes
  from `__file_open` instead.
- **Does not use `__file_addr`.** File tracking is automatic through the fd.
- **Symbolic:** The `SymbolicFS` creates the file, opens it (fd=3), writes
  data, and seeks. After the summary runs, `to_constraint()` generates
  variables:
  - `file_fd3_flags` — open flags (numeric, e.g., 578 = `O_RDWR|O_CREAT|O_TRUNC`)
  - `file_fd3_mode` — permissions (e.g., 420 = `0644`)
  - `file_fd3_offset` — final file offset
  - `file_fd3_size` — file size in bytes
  - `file_fd3_byte_N` — file content, byte by byte
- **Concrete:** `__file_create`/`__file_open`/`__file_write`/`__file_set_offset`
  in `sbv_sample.c` perform real OS operations. `sbv_open` tracks the fd via
  `fd_track_t`. At recording time, `sbv_record` reads the file and emits
  `D fd3 <flags> <mode> <offset> <nbytes> <hex>`.

When `data` is present, the file is opened with `"w+"` (read+write) instead of
`"w"` (write-only), so the function can read the pre-populated data.

### File (`type: pointer`) — Generated Code

Same as `descriptor`, plus an fd-to-FILE* conversion:

```c
int __fd_fp = __file_open(__fname_fp, "w");
FILE *fp = __FILE_from_fd(__fd_fp);
```

A temporary fd variable (`__fd_fp`) is created for the open. `__FILE_from_fd`
converts it to a `FILE*`. Tracking works the same way as `descriptor` —
through the underlying fd.

### Comparison Table

| Aspect                | `scalar`           | `memory (write)`       | `memory (read)`        | `file: name`           | `file: descriptor`     | `file: pointer`        |
|-----------------------|--------------------|------------------------|------------------------|------------------------|------------------------|------------------------|
| **C type**            | `int`, `size_t`... | `char*`, `void*`       | `char*`, `void*`       | `char*`                | `int`                  | `FILE*`                |
| **Symbolic init**     | `__sym_var_named`  | `__sym_var_array`      | `__sym_var_array`      | `__sym_var_array`      | via `__file_open`      | via `__file_open`      |
| **Setup code**        | None               | None                   | None                   | None                   | create+open+write+seek | create+open+write+seek |
| **Tagging**           | None               | `__mem_addr`           | None                   | `__file_addr`          | None (auto via fd)     | None (auto via fd)     |
| **Formula variables** | The var itself      | `mem_{name}_{i}`       | —                      | `file_{name}_exists`   | `file_fd{N}_*`         | `file_fd{N}_*`         |
| **Concrete record**   | Part of `Ret`      | `M` line               | —                      | `F` line               | `D` line               | `D` line               |
| **Skip in ArgGen?**   | No                 | No                     | No                     | No                     | Yes                    | Yes                    |

### Symbolic FS Constraints

From `sra.h`:

> *File names may be either concrete or symbolic strings. All other arguments
> must be concrete values.*

This means:
- **`name`/`path`** in `__file_create`, `__file_open`, `__file_exists`,
  `__file_delete` → may be symbolic
- **`fd`**, **`count`**, **`offset`**, **`size`**, **`mode`** → must always
  be concrete
- **`buffer`** in `__file_read`/`__file_write` → must be a concrete pointer
  (contents may be symbolic)

If a summary passes a symbolic value where a concrete one is required, the
symbolic engine raises `InvalidCountError` (or similar).
