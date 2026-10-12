Check if a variable is symbolic to prevent unwanted branching.

```c
void foo(int v){
    if(__is_symbolic(v)){
        ...
    }
    ...
}
```