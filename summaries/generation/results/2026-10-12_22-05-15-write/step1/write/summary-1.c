#include "sra.h"

#define O_ACCMODE 0003
#define O_RDONLY  0
#define O_APPEND  02000

/*
 * Summary of: ssize_t write(int fd, const void *buf, size_t count)
 *
 * Writes `count` bytes of `buf` to `fd` at its offset (at the end of the file
 * first, if opened with O_APPEND), advances the offset, and returns `count`.
 * Writes are never partial. Fails with -1 if `fd` is not open (EBADF) or not
 * open for writing (EBADF).
 *
 * `fd` may be `ite(cond, fd, -1)`. Its flags are then `ite(cond, flags, -1)`,
 * and `flags >> 31` is `ite(cond, 0, -1)`: the not-open case is handled by
 * masking with it rather than by branching on it.
 *
 * Branches:
 *  - read-only descriptor: fails. A not-open one never takes it, as -1 has
 *    every bit set and so an access mode of O_ACCMODE;
 *  - O_APPEND: the API's "a" does not append, so seek to the end first. The
 *    size may be an `ite` (unfolded) and `__file_set_offset` needs it concrete;
 *  - a symbolic `count`: the API needs it concrete, so fork once per value.
 */
ssize_t write(int fd, const void *buf, size_t count)
{
    const char *bytes = (const char *) buf;
    int flags = __file_flags(fd);
    int closed = flags >> 31;     // -1 if fd is not open, 0 otherwise

    if ((flags & O_ACCMODE) == O_RDONLY)
        return -1;

    if (flags & ~closed & O_APPEND) {
        ssize_t size = __file_size(fd);
        ssize_t end = __concretize(size);
        while (size != end)
            end = __concretize(size);
        __file_set_offset(fd, end);
    }

    // Fork once per possible count; past the loop, count == max
    size_t n = count;
    if (__is_symbolic(count)) {
        size_t max = __maximize(count);
        for (n = 0; n < max; n++)
            if (count == n)
                break;
    }

    // One byte at a time: __file_write stops at a concrete '\0', write does not
    for (size_t i = 0; i < n; i++)
        __file_write(fd, bytes + i, 1);

    // -1 | n is -1, and 0 | n is n
    return closed | n;
}
