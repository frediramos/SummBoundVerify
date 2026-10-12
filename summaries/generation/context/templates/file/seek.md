Compute a seek position: from 0, the current offset or the size, plus the offset. A negative result, or an unknown `whence`, fails (EINVAL). `__file_set_offset` needs it concrete: fork or unfold first.

```c
#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2

off_t foo(int fd, off_t offset, int whence){
    off_t base;

    if (whence == SEEK_SET)
        base = 0;
    else if (whence == SEEK_CUR)
        base = __file_offset(fd);
    else if (whence == SEEK_END)
        base = __file_size(fd);     // may be symbolic: unfold it
    else
        return -1;

    off_t pos = base + offset;
    if (pos < 0)
        return -1;

    return __file_set_offset(fd, pos);
}
```
