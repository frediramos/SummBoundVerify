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
- **Note:** This function is mean for constraints only.

``` c
cnstr_t _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2, size_t len, size_t len2); -> cond ? var1 : var2
```
- **Note:** This function is mean for variables only.
