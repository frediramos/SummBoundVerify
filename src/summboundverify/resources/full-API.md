## Core Primitives

```c
long maximize(symbolic var);
```
- Takes the symbolic variable `var` and  returns the maximum value that it may denote given the current path condition.


```c
long minimize(symbolic var);
```
- Takes the symbolic variable `var` and  returns the minimum value that it may denote given the current path condition.


```c
symbolic sym_var(size_t size);
```
- Returns a new symbolic variable with a uniquely generated identifier and denoting a value with `size` bits.


```c
symbolic sym_var_named(char* name, size_t size);
```
- Returns a new symbolic variable identified by `name` and denoting a value with `size` bits.


```c
symbolic sym_var_array(char* name, size_t index, size_t size);
```
- Returns a new symbolic variable, identified by an array `name`
and an <index>, denoting a value with <length> bits. Used to fill symbolic arrays.


```c
int is_symbolic(symbolic var);
```
- Checks if variable `var` bits is symbolic.


```c
int is_sat(cnstr_t cnstr);
```
- Calls the SMT solver to check if the constraint `cnstr` is
satisfiable given the current path condition.


```c
int is_certain(cnstr_t cnstr);
```
- Calls the SMT solver to check if the constraint `cnstr` is
certainly true given the current path condition.


```c
void assume(cnstr_t cnstr)
```
- Adds the constraint `cnstr` to the current path condition
of the symbolic state.


```c
void push_pc()
```
- Saves the current path condition by creating a copy and pushing it onto the path condition stack.

- This operation is typically used before exploring a new execution branch so that the current condition can later be restored.


```c
void pop_pc()
```
- Restores the previous path condition by popping the top element from the path condition stack.

- This is typically used after finishing the exploration of a branch, reverting the path condition to its earlier state.


## Constraints

``` c
cnstr_t _NOT_(cnstr_t cnstr); -> ¬cnstr
```

``` c
cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2); -> cnstr1 ∨ cnstr2
```

``` c
cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2); -> cnstr1 ∧ cnstr2
```

``` c
cnstr_t _LT_(symbolic var1, symbolic var2); -> var1 < var2 (signed)
```

``` c
cnstr_t _LE_(symbolic var1, symbolic var2); -> var1 ≤ var2 (signed)
```

``` c
cnstr_t _GT_(symbolic var1, symbolic var2); -> var1 > var2 (signed)
```

``` c
cnstr_t _GE_(symbolic var1, symbolic var2); -> var1 >= var2 (signed)
```

``` c
cnstr_t _EQ_(symbolic var1, symbolic var2); -> var1 = var2
```

``` c
cnstr_t _NEQ_(symbolic var1, symbolic var2); -> var1 ≠ var2
```

``` c
cnstr_t _ULT_(symbolic var1, symbolic var2); -> var1 < var2 (unsigned)
```

``` c
cnstr_t _ULE_(symbolic var1, symbolic var2); -> var1 ≤ var2 (unsigned)
```

``` c
cnstr_t _UGT_(symbolic var1, symbolic var2); -> var1 > var2 (unsigned)
```

``` c
cnstr_t _UGE_(symbolic var1, symbolic var2); -> var1 >= var2 (unsigned)
```

``` c
cnstr_t _ITE_(cnstr_t cond, cnstr_t cnstr1, cnstr_t cnstr2); -> cond ? cnstr1 : cnstr2
```
- **Note:** This function is meant for constraints only.

``` c
cnstr_t _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2); -> cond ? var1 : var2
```
- **Note:** This function is meant for variables only.


# Lists
This section of the API describes the functions for creating and manipulating lists of bytes (`list_t`).

```c
list_t lst_mk();
```
- Returns a new empty list.

```c
list_t lst_cons(symbolic value, list_t lst);
```
- Prepends a `value` to `lst`.

```c
cnstr_t lst_empty(list_t lst);
```
- Returns `True` if `lst` is empty, and `False` otherwise. 

```c
list_t lst_tl(list_t lst); 
```
- Returns the tail of `lst`, that is, `lst` without its first element.

```c
symbolic lst_hd(list_t lst);
```
- Returns the first element (head) of `lst`.

```c
size_t lst_len(list_t lst);
```
- Returns the number of elements contained in `lst`.

```c
list_t lst_nbytes(char c, size_t n);
```
- Returns a new list containing `n` copies of the byte `c`.

```c
list_t lst_zeros(size_t n);
```
- Returns a new list containing `n` null (`'\0'`) bytes.

```c
void cond_write(void* ptr, symbolic c, cnstr_t pc);
```
- Stores a conditional value at the memory address pointed to by `ptr`. The resulting value is an if-then-else expression: if `pc` evaluates to true, the byte at `ptr` is `c`; otherwise, it retains its previous value.

- If `ptr` is symbolic, the write is performed over the set of possible addresses represented by `ptr`. For each affected address, the resulting value is encoded as an if-then-else expression that captures both the path condition `pc` and whether that address is selected by `ptr`.


# Heap

```c
void* mem_alloc(size_t nbytes); 
```
- Allocates `nbytes` bytes of memory on the heap and returns a pointer to the allocated region.

```c
void mem_free(void* ptr);
```
- Frees the heap region pointed to by `ptr`. The pointer must have been returned by `mem_alloc`.

```c
size_t n_allocd(void* ptr);
```
- Returns the number of allocated bytes pointed to by `ptr`. The pointer must have been returned by `mem_alloc`.

```c
size_t allocd(void* ptr);
```
- Throws and exception if the memory pointed to by `ptr` does not have `r/w` permissions. The input `ptr` does **not** need to be a mallocd heap pointer.


## Validation Primitives

```c
state_t save_current_state();
```
- Saves a copy of the current symbolic state. Returns a `state_t`.


```c
cnstr_t get_cnstr(symbolic var, size_t size);
```
- Builds a formula denoting the conjunction of the current path condition and `Ret == <var>`
- `Ret` is fresh a symbolic variable.


```c
void store_cnstr(char* name, cnstr_t constraint);
```
- Stores the given constraint `cnstr` associating it with the key `name`.

```c
void mem_addr(char* name, void* addr, size_t n);
```
- Marks the `n+1` consecutive memory addresses, starting from `addr`inclusive, to be evaluated by the summary validation tool.


```c
result_t check_implications(char* summ, char* cncrt);
```
- Checks the correctness implications for the previously stored constraints associated with the keys `summ` and `cncrt`.
- Returns a `result_t`.


```c
void halt_all(state_t state);
```
- Halts all current execution paths. Resumes a single path from `state`.
- If `state` is `NULL`, resumes from the current state.

```c
void print_counterexamples(result_t result);
```
- Prints the validation results.
- Prints counterexample models for the implications proven wrong.
