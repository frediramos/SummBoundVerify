Unfold and concretize a nested if-then-else expression.

```c
// Symbolic size if type: ite(cond1, size1, ite(cond2, size2, ...))
ssize_t end = __concretize(size);
while (size != end)
    end = __concretize(size);
foo(end) // Use concrete value
```