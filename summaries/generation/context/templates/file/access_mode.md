Check the descriptor's access mode, which the API does not enforce: reading needs O_RDONLY or O_RDWR, writing O_WRONLY or O_RDWR (EBADF otherwise).

```c
#define O_ACCMODE 0003
#define O_RDONLY  0
#define O_WRONLY  1

ssize_t foo(int fd, void *buf, size_t count){
    int flags = __file_flags(fd);

    // Reading
    if (flags == -1 || (flags & O_ACCMODE) == O_WRONLY)
        return -1;

    // Writing would be: (flags & O_ACCMODE) == O_RDONLY
    ...
}
```
