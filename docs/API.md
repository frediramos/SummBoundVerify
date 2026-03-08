## Constraints


``` c
cnstr_t _NOT_(cnstr_t cnstr) -> ¬cnstr
```

``` c
cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2) -> cnstr1 ∨ cnstr2
```

``` c
cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2) -> cnstr1 ∧ cnstr2
```

``` c
cnstr_t _LT_(symbolic var1, symbolic var2) -> var1 < var2 (signed)
```

``` c
cnstr_t _LE_(symbolic var1, symbolic var2) -> var1 ≤ var2 (signed)
```

``` c
cnstr_t _GT_(symbolic var1, symbolic var2) -> var1 > var2 (signed)
```

``` c
cnstr_t _GE_(symbolic var1, symbolic var2) -> var1 >= var2 (signed)
```

``` c
cnstr_t _EQ_(symbolic var1, symbolic var2) -> var1 = var2
```

``` c
cnstr_t _NEQ_(symbolic var1, symbolic var2) -> var1 ≠ var2
```

``` c
cnstr_t _ULT_(symbolic var1, symbolic var2) -> var1 < var2 (unsigned)
```

``` c
cnstr_t _ULE_(symbolic var1, symbolic var2) -> var1 ≤ var2 (unsigned)
```

``` c
cnstr_t _UGT_(symbolic var1, symbolic var2) -> var1 > var2 (unsigned)
```

``` c
cnstr_t _UGE_(symbolic var1, symbolic var2) -> var1 >= var2 (unsigned)
```

``` c
cnstr_t _ITE_(cnstr_t cond, cnstr_t cnstr1, cnstr_t cnstr2) -> cond ? cnstr1 : cnstr2
```

``` c
cnstr_t _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2, size_t len, size_t len2) -> cond ? var1 : var2
```
