Check a file's permission bits before opening it (EACCES). `__file_open` itself ignores them, so read them through a descriptor first. The owner's bits: 0400 read, 0200 write.

```c
int foo(const char *pathname, int flags){
    mode_t mode;

    int probe = __file_open(pathname, "r");
    __file_mode(probe, &mode);
    __file_close(probe);

    int reads  = (flags & O_ACCMODE) != O_WRONLY;
    int writes = (flags & O_ACCMODE) != O_RDONLY;

    if ((reads && !(mode & 0400)) || (writes && !(mode & 0200)))
        return -1;
    ...
}
```
