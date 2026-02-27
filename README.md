<p align="center"> <h1 align="center"> SummBoundVerify </h1> </p> 
<p align="center"><strong>* Validate Symbolic Summaries (for C) *</strong></p>

<p align="center">
  <a href="#bare-metal-installation">Installation</a> •
  <a href="#docker-container">Docker</a> •
  <a href="#examples">Examples</a> •
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

- `config.txt` - The test configuration;
- `strlen.c` — The summary under test;
- `concrete.c` — The concrete implementation against which the summary is validated.

### Command
The `make` target wraps the following tool invocation:

```sh
summbv \
    --arraysize 3 \ 
    -func concrete.c \
    --summname strlen \
    --lib strlen.c \
    --compile x86
``` 

### Breakdown

- `arraysize 3` — bounds the size of symbolic arrays to 3;
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
summbv 
    --arraysize 3 \ 
    -func concrete.c \
    --summname strlen \
    --lib strlen.c \
    --compile x86 \
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
    -memory
    --func concrete.c \
    --summ memcpy.c \
    --maxvalue 5 \
    --compile x86
```

### Breakdown
- `memory` - Tells the tool that the memory pointed to by `dest` and `src` is to be considered for evaluation;
- `maxvalue 5` — bounds the maximum value for symbolic scalar inputs to `5`.

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

By default, this will generate a file called `test.c` containing the symbolic test where `strlen` is called with a symbolic string of **size 5**. Additionally, instead of the default value **5**, the length of the symbolic string used as input argument can be specified using the `--arraysize` flag:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c --arraysize=3
```

## Generate multiple tests
To generate a single test file containing multiple executions for different arrays sizes one can also pass an array of values to the `--arraysize` flag:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c --arraysize 3 5 7 -compile
```


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

For some ``libc`` functions, using fully symbolic arguments can lead to unbound loops in the concrete functions. To constrain numeric values one can use the ``--maxvalue`` flag. For instance considering a test for the ``memcpy(void *dest, const void *src, size_t len)`` function, the command:

```sh
summbv -summ summ_memcpy.c -func concrete_memcpy.c -maxvalue=5
```

will generate a test where the ``len`` argument is constrained to be lower or equal than ``5``.

## Evaluate memory functions
By default the summary validation tool only takes into account the generated paths and corresponding return values. Hence, in order to evaluate a summary for a function with memory side effects such ``memcpy``, one can use the ``-memory`` flag:

```sh
summbv -summ summ_memcpy.c -func concrete_memcpy.c -maxvalue=5 -memory
```
This flag marks the relevant memory addresses in the summary's execution so that they are also be evaluated.

## Configuration Files

In alternative to the command line interface, one can also pass a configuration file using the ``-config`` flag. For instance, considering the configuration file (``config.txt``): 

```
arraysize 3 5 7
func concrete_strlen.c
summ summ_strlen.c
compile x86
```

The command:
```sh
summbv -config config.txt
```
is equivalent to:
```sh
summbv -summ summ_strlen.c -func concrete_strlen.c --arraysize 3 5 7 -compile
```

### All Config file options

The options allowed in the configuration file mirror some flag options offered in the command line interface:

```
func  concrete.c          // -func            (Path to file containing the concrete function)
summ  summ.c              // -summ            (Path to file containing the target summary)
summname  strlen          // --summname       (Name of the summary in the given path)
funcname  summ_strlen     // --funcname       (Name of the concrete function in the given path)
arraysize 5 | [5,7]       // --arraysize      (Maximum array size of each test (default:5))
nullbytes 3 | [2,3]       // --nullbytes      (Specify array indexes to place null bytes)
defaultvalues {1:'NULL'}  // --defaultvalues  (Specify default const values for input variables)
maxvalue 5                // --maxvalue       (Provide an upper bound for numeric values)
maxnames len              // --maxnames       (Numeric value names to be constrained)
concretearray {1:[0]}     // --concretearray  (Place concrete values in selected array indexes)
lib lib.c                 // --lib            (Path to external files required for compilation)
compile x86               // --compile        (Compile the generated test)
```

## Special Configurations

## Array Size 

By passing an array of type ``[<val>,<val2>,...]`` instead of a single value, one can specify the array size of each function argument. For instance the configuration:
```sh
arraysize [5,7]  // --arraysize [5,7] 
```
specifies that the **first** argument in the function must have ``size = 5`` and the **second** must have ``size = 7``.

## Null Bytes

This options allows to specify the array indexes where null bytes should be placed. By passing an array of type ``[<index1>,<index2>,...]`` instead of a single value, one can specify the null bytes' index of each argument. For instance, the configuration:
```sh
arraysize [2,3]  // --nullbytes [2,3] 
```
specifies that the **first** argument is null terminated at ``index = 2`` and the **second** is null terminated at ``index = 3``.

## Default Values
This option allows to specify a constant value for an input variable to be initialized with. For instance, assuming that the **first** function argument is ``char **endptr``, the configuration:
```sh
defaultvalues {1:'NULL'}  // --defaultvalues {1:'NULL'}
```
specifies that in the validation test, the argument ``endptr`` is initialized as:

```sh
char **endptr = NULL;
```
### Special ``&`` init value

In some cases one may need to pass to a function a reference to a declared variable. To this end, assuming that the **first** function argument is ``char **save_ptr``, one can use the configuration:

```sh
defaultvalues {1:'&'}  // --defaultvalues {1:'&'}
```

which generates a validation test such that:

```sh
char *save_ptr;
foo(&save_ptr, ... );
```


## Concrete Arrays
By default all positions of an array are symbolic. One can use the ``concretearray`` (``--concretearray``) to make certain array positions concrete.

### Make indexes concrete
To make specific array indexes hold concrete values one can pass a dictionary of the type ``{<arg>:[<indexes>]}``. For instance, the configuration:

```sh
concretearray {1:[0,1]}  // --concretearray {1:[0,1]}
```

generates a test such that an array as the **first** function argument holds concrete values at indexes ``0`` and ``1``.


### Make *N* positions concrete
To make a number of array indexes hold concrete values one can pass a dictionary of the type ``{<arg>:['N']}``, where ``N`` is the number of indexes to be made concrete. For instance, the configuration:

```sh
concretearray {1:['2']}  // --concretearray {1:['2']}
```

generates a test such that **two** random indexes of an array as the **first** function argument are concrete.


# License

This project is licensed under the [GPL-3.0 License] -- see [LICENSE] for details.

[LICENSE]: ./LICENSE