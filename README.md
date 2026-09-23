<p align="center"> <h1 align="center"> SummBoundVerify </h1> </p> 
<p align="center"><strong>* Validate Symbolic Summaries (for C) *</strong></p>

<p align="center">
  <a href="#bare-metal-installation">Installation</a> •
  <a href="#docker-container">Docker</a> •
  <a href="#examples">Examples</a> •
  <a href="#validation-engines">Engines</a> •
  <a href="#argspec">Argspec</a> •
  <a href="#documentation">Docs</a> •
  <a href="#license">License</a>
</p>

<br>
<br>


## Bare Metal Installation

### Python Virtual Environment (Recommended)

We strongly recommend installing `SummBoundVerify` inside a Python virtual environment to avoid dependency conflicts.

SummBoundVerify has been tested with `Python` **`3.12`**, but it should work with any modern Python version (**3.10+**).

One convenient way to manage virtual environments is with [`virtualenvwrapper`](https://virtualenvwrapper.readthedocs.io/en/latest/install.html).

After installation, create and activate a new virtual environment with:

```bash
mkvirtualenv sbv
```
---
Alternatively, one can use standard Python `venv`:

```bash
python3 -m venv mkvirtualenv sbv-env
```
After creating it, it can be activated with:
```bash
source sbv-env/bin/activate
```

## Installation
Before installing, make sure your Python virtual environment is activated.

### To install:
Run the installation script from the project root:
```sh
./install.sh
```
This will install the tool and set up the required dependencies in the active environment.

### To uninstall:
To remove the installed components:
```sh
cd scripts && ./uninstall
```
### Verify the Installation
You can verify that everything is working correctly by running the `strlen` example test:
```sh
cd examples/libc/strlen && make test
```

The output should include: `Test Passed!`

## Docker Container
We also provide a self-contained Docker environment for running the tool without installing any dependencies locally.

To build the image and start a temporary container with the tool pre-installed, run:

```sh
./docker-run [path]
```
The `path` argument defaults to the current directory if not provided.

<br>

# Examples 
One can find illustrative examples of how to use the tool in the `examples/libc` directory.

To run these examples inside the Docker container, execute:
```sh
./docker-run examples/libc
```
This will start the container with the `examples/libc` directory mounted and ready to use.


## `strlen`
This example demonstrates how to validate a simple summary from the C standard library function:
```c
size_t strlen(char * s)
```

To generate and compile a validation test, use:

```sh
cd strlen && make
```

### Relevant files

- `config.yaml` - The test configuration;
- `argspec.yaml` — Argument specification (semantic roles and constraints);
- `strlen.c` — The summary under test;
- `concrete.c` — The concrete implementation against which the summary is validated.

### Command
The `make` target wraps the following tool invocation:

```sh
summbv \
    -func concrete.c \
    --summname strlen \
    --lib strlen.c \
    --compile x86 \
    --argspec argspec.yaml
``` 

Where `argspec.yaml` contains:
```yaml
str:
  type: char*
  semantic: memory
  memory:
    type: read
    size: 3
```

### Breakdown

- `argspec argspec.yaml` — provides the argument specification, including array size bounds;
- `func concrete.c` — specifies the concrete implementation file;
- `summname strlen` — selects the summary (function) name to be called;
- `lib strlen.c` — provides the summary file;
- `compile x86` — compiles the generated validation harness for the x86 target.

<br>

`summbv` automatically generates a validation testing harness, in C, that checks whether the summary in `strlen.c` is an *under-* or an *over-approximation* of the corresponding concrete implementation.

The validation test is given in the file: `strlen_validation.c`.

### **Run**

To symbolically execute the previously generated test use:

```sh
make run
```

The `make run` target behaves like `make`, but additionally executes the generated validation test.

Concretely, it invokes the same command as before, with the extra `-run` flag:

```sh
summbv \
    -func concrete.c \
    --summname strlen \
    --lib strlen.c \
    --compile x86 \
    --argspec argspec.yaml \
    -run
``` 

### Output

In addition to the standard terminal output, the command produces a JSON file containing the validation results. For example:

```json
{
  "strlen_validation.test_1": {
    "result": "Exact",
    "counterexamples": {}
  }
}
```

### Field Description

`"result"` : `"Exact"` — the summary is both under- and over-approximating thus precisely matches the concrete implementation for the explored input space.

`"counterexamples"` — contains counterexample inputs if discrepancies are found (empty in this case).

## `memcpy`
This example demonstrates how to validate a summary with memory side effects. In particular, the `memcpy` function:

```c
void* memcpy(void *dest, void *src, size_t n)
```

To generate and compile a validation test, again, use:

```sh
cd memcpy && make
```

### Command
In this example, the `make` target wraps the following command:

```sh
summbv \
    -func concrete.c \
    -summ memcpy.c \
    --compile x86 \
    --argspec argspec.yaml
```

Where `argspec.yaml` contains:
```yaml
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

### Breakdown
- `memory.type: write` tells the tool that the memory pointed to by `dest` is to be considered for evaluation;
- `scalar.maxvalue: 5` bounds the `n` argument to `≤ 5`;
- `memory.size: 5` sets the symbolic array size for `dest` and `src`.

The generated validation test is available in:

```sh
memcpy_validation.c
```

### Run

To symbolically execute the generated validation test, also use:

```sh
make run
```

### Output 

The JSON file containing the validation results shows:

```json
{
  "memcpy_validation.test_1": {
    "result": "Under-approximation",
    "counterexamples": {
      "Over-approximation": {
        "dest": {
          "dest_0": 0,
          "dest_1": 0,
          "dest_2": 0,
          "dest_3": 0,
          "dest_4": "Not in model"
        },
        "src": {
          "src_0": "a",
          "src_1": "b",
          "src_2": "c",
          "src_3": "d",
          "src_4": "Not in model"
        },
        "n": 2,
        "ret": 2147417906,
        "memory": {
          "dest": {
            "mem_dest_0": "a",
            "mem_dest_1": "b",
            "mem_dest_2": 0,
            "mem_dest_3": 0,
            "mem_dest_4": 0
          },
          "src": {
            "mem_src_0": "a",
            "mem_src_1": "b",
            "mem_src_2": "c",
            "mem_src_3": "d",
            "mem_src_4": 0
          }
        }
      }
    }
  }
}
```

The output indicates:

- `"result": "Under-approximation"` — the summary does **not** fully capture the behaviour of the concrete implementation.
- `"counterexamples"` — provides a concrete input demonstrating the mismatch.
- The `"Over-approximation"` block details the scenario where the summary admits behaviour not matched by the concrete implementation, including symbolic inputs and memory state.

<br>
<br>

# Validation Engines

A summary can be validated in two ways, selected with `--engine`:

```sh
summbv -config config.yaml --engine se     # symbolic execution (default)
summbv -config config.yaml --engine fuzz   # fuzzing
summbv -config config.yaml --engine se fuzz # both, side by side
```

**`se`** runs *both* the summary and the concrete implementation under `angr`
and proves an implication between them. It is the stronger result — it grades
the summary as *exact*, *under-* or *over-approximating* — and it is what the
examples above use.

**`fuzz`** executes only the **summary** symbolically, keeping one formula per
path. The concrete function is compiled and run **natively** under AFL++, at
full speed, and each `(input, result)` pair it produces is checked against
those formulas. The summary is executed symbolically in either engine; what
changes is whether the concrete function is.

The formulas are printed before the campaign starts, one per summary path,
under `==> Summary Constraints` — the same thing `se` shows as part of its
verdict. They are what every sample is checked against, so a `mismatched`
verdict can be read next to the claim it refutes.

That difference is the point. The concrete function is the hard half — loops,
allocation, recursion — and when `angr` cannot follow it, symbolic execution
does not return a weaker verdict, it returns none at all. Sampling never
executes it symbolically, so it handles precisely the targets `se` refuses.

The trade is that sampling **cannot prove a summary correct**. It is a
falsification test: it either produces a real input the summary gets wrong, or
it says nothing was found.

### Verdicts

Written to `<test>_check.json` and printed at the end of the run:

| verdict      | meaning |
|--------------|---------|
| `passed`     | every sample was admitted by the summary. Provisional, never a proof |
| `mismatched` | a refutation: a real input on which the summary cannot produce the real result |
| `starved`    | nothing was checked; the verdict carries no weight |

### Requirements

Sampling needs **AFL++** (`apt install afl++`) and a **32-bit toolchain**
(`gcc-multilib`, `libc6-dev-i386`). The generated API stubs `typedef unsigned
int size_t`, so the symbolic side is 32-bit whatever the host is, and only a
32-bit sampler produces comparable values.

### Relevant flags

```
--engine se | fuzz          // engine(s) to run; "se fuzz" runs both (default: se)
--execs 10000               // inputs to try when sampling (default: 10000)
--timeout 1800              // seconds, per engine
```

Symbolic execution is skipped automatically — *even when asked for
explicitly* — on targets `angr` cannot finish, currently recursive functions
and floating point. The substitution is announced rather than made quietly.

<br>
<br>

# Argspec

An **argspec** is a YAML file that describes each function argument's semantic
role (`scalar`, `memory`, or `file`) and test-generation constraints (array
size, max value, null bytes, etc.).

It consolidates per-argument configuration that was previously spread across
CLI flags and config file options.

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

Pass it with `--argspec argspec.yaml` or add `argspec: argspec.yaml` to a config file.

For the full schema reference, including all supported properties and examples,
see **[ARGSPEC.md](ARGSPEC.md)**.

<br>
<br>

# Documentation
To obtain a full description of our test generation tool one can use the flag `-h`
```sh
summbv -h
```

## Generate a simple validation test 

Given a concrete function for ``strlen`` and a corresponding summary (files ``strlen.c`` and ``concrete.c``) one can generate a simple validation test using:

```sh
summbv -summ strlen.c -func concreten.c
```

By default, this will generate a file called `test.c` containing the symbolic test where `strlen` is called with a symbolic string of **size 5**. The array size for each argument can be configured in the argspec YAML via the ``memory.size`` property (see [ARGSPEC.md](ARGSPEC.md)).

## Compile to a binary
In order to execute the generated tests in a symbolic execution tool, a binary file is usually required. To this end, one can pass the `--compile` flag:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c -compile
```

This automatically compiles the generated test to an *x86* binary. Alternatively, the target *arch* can be specified. For instance, the command:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c -compile=x64
```
compiles the test to *x84_64* architecture.

## Function names and Libraries

To evaluate a tool summary (not implemented in a separate file) one can simply specify its name using the ``--summname`` flag: 

```sh
summbv -summname strlen -func concrete_strlen.c -compile=x64
```

Additionally, it is often the case that a summary or concrete function may not be self-contained in a single C file. To this end, when compiling a test using the `--compile` flag one can also pass additional files with the ``--lib`` flag:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c -compile --lib lib1.c lib2.c 
```


## Constrain numeric values

For some ``libc`` functions, using fully symbolic arguments can lead to unbound loops in the concrete functions. Numeric values are constrained through the argspec YAML, using the ``maxvalue`` property under the ``scalar`` block:

```yaml
# argspec.yaml
n:
  type: size_t
  semantic: scalar
  scalar:
    maxvalue: 5
```

This generates a test where the ``n`` argument is constrained to be lower or equal than ``5``.

## Evaluate memory functions
By default the summary validation tool only takes into account the generated paths and corresponding return values. To evaluate a summary for a function with memory side effects such as ``memcpy``, use an argspec that marks the relevant pointer arguments with ``semantic: memory``:

```yaml
# argspec.yaml
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

```sh
summbv -summ summ_memcpy.c -func concrete_memcpy.c --argspec argspec.yaml
```

The ``memory.type`` field controls which memory regions are tagged for evaluation:
- ``read`` — read-only, not tagged (e.g. ``src`` in ``memcpy``);
- ``write`` — read-write, tagged with ``__mem_addr``.

Memory evaluation is enabled automatically when any argument has ``semantic: memory`` with ``memory.type: write``.

## Configuration Files

In alternative to the command line interface, one can also pass a YAML configuration file using the ``-config`` flag. For instance, considering the configuration file (``config.yaml``):

```yaml
func: concrete_strlen.c
summ: summ_strlen.c
compile: x86
argspec: argspec.yaml
```

The command:
```sh
summbv -config config.yaml
```
is equivalent to:
```sh
summbv -summ summ_strlen.c -func concrete_strlen.c --compile x86 --argspec argspec.yaml
```

### All Config file options

The options allowed in the configuration file mirror the flag options offered in the command line interface:

```yaml
func: concrete.c           # -func            (Path to file containing the concrete function)
summ: summ.c               # -summ            (Path to file containing the target summary)
summname: strlen            # --summname       (Name of the summary in the given path)
funcname: summ_strlen       # --funcname       (Name of the concrete function in the given path)
argspec: argspec.yaml       # --argspec        (YAML file with argument semantics and constraints)
lib: lib.c                  # --lib            (Path to external files required for compilation)
compile: x86                # --compile        (Compile the generated test)
engine: [se, fuzz]          # --engine         (Validation engine(s); default: se)
execs: 10000                # --execs          (Inputs to try when sampling)
timeout: 1800               # -timeout         (Execution timeout, in seconds)
```

> **Note:** Per-argument constraints (array size, max value, null bytes, default values, concrete arrays, etc.)
> are specified in the argspec YAML file. See [ARGSPEC.md](ARGSPEC.md) for the full schema reference.


# License

This project is licensed under the Apache 2.0 License -- see [LICENSE] for details.

[LICENSE]: ./LICENSE
