# SummBoundVerify

## Prequisites
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
Once your virtual environment is activated:

### To install:
```sh
cd scripts && ./install.sh
```

### To uninstall:
```sh
cd scripts && ./uninstall
```

# Basic Usage
To obtain a full description of our test generation tool one can use the flag `-h`
```sh
summbv -h
```

## Generate a simple test for ``strlen`` 

Given a concrete function for ``strlen`` and a corresponding summary (files ``summ_strlen.c`` and ``concrete_strlen.c``) one can generate a simple validation test using:

```sh
summbv -summ summ_strlen.c -func concrete_strlen.c
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

To evaluate a tool summary (not implemented in a separate file) one can simply specify its name using the ``--summ_name`` flag: 

```sh
summbv -summ_name strlen -func concrete_strlen.c -compile=x64
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

# Configuration Files

In alternative to the command line interface, one can also pass a configuration file using the ``-config`` flag. For instance, considering the configuration file (``config.txt``): 

```
array_size 3 5 7
func_file concrete_strlen.c
summ_file summ_strlen.c
compile_arch x86
```

The command:
```sh
summbv -config config.txt
```
is equivalent to:
```sh
summbv -summ summ_strlen.c -func concrete_strlen.c --arraysize 3 5 7 -compile
```

## All Config file options

The options allowed in the configuration file mirror some flag options offered in the command line interface:

```
func_file  concrete.c       // -func            (Path to file containing the concrete function)
summ_file  summ.c           // -summ            (Path to file containing the target summary)
summ_name  strlen           // --summ_name      (Name of the summary in the given path)
func_name  summ_strlen      // --func_name      (Name of the concrete function in the given path)
array_size 5 | [5,7]        // --arraysize      (Maximum array size of each test (default:5))
null_bytes 3 | [2,3]        // --nullbytes      (Specify array indexes to place null bytes)
default_values {1:'NULL'}   // --defaultvalues  (Specify default const values for input variables)
max_num 5                   // --maxvalue       (Provide an upper bound for numeric values)
max_names len               // --maxnames       (Numeric value names to be constrained)
concrete_array {1:[0]}      // --concretearray  (Place concrete values in selected array indexes)
lib lib.c                   // --lib            (Path to external files required for compilation)
compile_arch x86            // --compile        (Compile the generated test)
```

# Special Configurations

## Array Size 

By passing an array of type ``[<val>,<val2>,...]`` instead of a single value, one can specify the array size of each function argument. For instance the configuration:
```sh
array_size [5,7]  // --arraysize [5,7] 
```
specifies that the **first** argument in the function must have ``size = 5`` and the **second** must have ``size = 7``.

## Null Bytes

This options allows to specify the array indexes where null bytes should be placed. By passing an array of type ``[<index1>,<index2>,...]`` instead of a single value, one can specify the null bytes' index of each argument. For instance the configuration:
```sh
array_size [2,3]  // --nullbytes [2,3] 
```
specifies that the **first** argument is null terminated at ``index = 2`` and the **second** is null terminated at ``index = 3``.

## Default Values
This option allows to specify a constant value for an input variable to be initialized with. For instance assuming that the **first** function argument is ``char **endptr``, the configuration:
```sh
default_values {1:'NULL'}  // --defaultvalues {1:'NULL'}
```
specifies that in the validation test, the argument ``endptr`` is initialized as:

```sh
char **endptr = NULL;
```
### Special ``&`` init value

In some cases one may need to pass to a function a reference to a declared variable. To this end, assuming that the **first** function argument is ``char **save_ptr``, one can use the configuration:

```sh
default_values {1:'&'}  // --defaultvalues {1:'&'}
```

which generates a validation test such that:

```sh
char *save_ptr;
foo(&save_ptr, ... );
```


## Concrete Arrays
By default all positions of an array are symbolic. One can use the ``concrete_array`` (``--concretearray``) to make certain array positions concrete.

### Make indexes concrete
To make specific array indexes hold concrete values one can pass a dictionary of the type ``{<arg>:[<indexes>]}``. For instance, the configuration:

```sh
concrete_array {1:[0,1]}  // --concretearray {1:[0,1]}
```

generates a test such that an array as the **first** function argument holds concrete values at indexes ``0`` and ``1``.


### Make *N* positions concrete
To make a number of array indexes hold concrete values one can pass a dictionary of the type ``{<arg>:['N']}``, where ``N`` is the number of indexes to be made concrete. For instance, the configuration:

```sh
concrete_array {1:['2']}  // --concretearray {1:['2']}
```

generates a test such that **two** random indexes of an array as the **first** function argument are concrete.