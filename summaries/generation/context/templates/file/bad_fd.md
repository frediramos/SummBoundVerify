Fail on a descriptor that is not open (EBADF): `__file_flags` returns -1 for it.

```c
int foo(int fd){
    int flags = __file_flags(fd);
    if (flags == -1)
        return -1;
    ...
}
```
