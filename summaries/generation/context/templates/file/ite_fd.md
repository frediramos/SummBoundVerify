A descriptor from a symbolic name may be `ite(cond, fd, -1)`. Pass it to the API as is: the result is `ite(cond, <result>, <error>)`, so the failure case needs no branch.

```c
ssize_t foo(int fd, void *buf, size_t count){
    // No `if (fd < 0)` needed for the API's own failure
    return __file_read(fd, buf, count);
}
```
