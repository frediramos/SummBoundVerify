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
