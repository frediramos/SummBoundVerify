Map `open` flags onto the API. `__file_open` never creates a file, and its mode string only sets `__file_flags`: "w" does not truncate and "a" does not append. Create, truncate and set the mode explicitly.

```c
#define O_ACCMODE 0003
#define O_WRONLY  01
#define O_RDWR    02
#define O_CREAT   0100
#define O_EXCL    0200
#define O_TRUNC   01000
#define O_APPEND  02000

int foo(const char *pathname, int flags, mode_t mode){
    int exists = __file_exists(pathname);

    if (exists && (flags & O_CREAT) && (flags & O_EXCL))
        return -1;                          // EEXIST
    if (!exists && !(flags & O_CREAT))
        return -1;                          // ENOENT

    // The access mode, and O_APPEND, as an fopen mode string
    const char *how;
    if ((flags & O_ACCMODE) == O_RDWR)
        how = (flags & O_APPEND) ? "a+" : "r+";
    else if ((flags & O_ACCMODE) == O_WRONLY)
        how = (flags & O_APPEND) ? "a" : "w";
    else
        how = "r";

    if (!exists)
        __file_create(pathname);

    int fd = __file_open(pathname, how);

    if (!exists)
        __file_set_mode(fd, mode & ~022);   // the umask applies on creation
    if (flags & O_TRUNC)
        __file_set_size(fd, 0);

    return fd;
}
```
