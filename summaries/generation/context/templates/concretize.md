Concretize a symbolic variable and constrain its value. The solver decides the concrete value.

```c
int foo(size_t count){
    size_t n = __concretize(count);
    __assume(_EQ_(count, n));
    ...
}
```