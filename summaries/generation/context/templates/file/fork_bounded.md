Fork once per possible value of a bounded symbolic variable, when the API needs it concrete. Unlike `__concretize`, every value is covered.

```c
ssize_t foo(int fd, void *buf, size_t count){
    if (!__is_symbolic(count))
        return __file_read(fd, buf, count);

    size_t max = __maximize(count);
    for (size_t n = 0; n < max; n++)
        if (count == n)
            return __file_read(fd, buf, n);    // n is concrete here

    return __file_read(fd, buf, max);
}
```
