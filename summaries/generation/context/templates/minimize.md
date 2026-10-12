Minimize a symbolic variable and constrain its value.

```c
void foo(size_t count){
    size_t n = __minimize(count);
    __assume(_EQ_(count, n));
    ...
}
```