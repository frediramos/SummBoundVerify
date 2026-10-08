typedef unsigned int size_t;
typedef int ssize_t;

#define O_ACCMODE 0003
#define O_RDONLY  0
#define O_APPEND  02000

/*
 * Summary of: ssize_t write(int fd, const void *buf, size_t count)
 *
 * Branches as little as possible; the two forks below are needed:
 *
 * - `fd` not open (`flags == -1`) or opened read-only: fail (EBADF), even
 *   when `count` is 0. If `fd` is `ite(cond, fd, -1)`, `flags` is
 *   `ite(cond, flags, -1)`, so this forks on `cond`.
 * - `O_APPEND`: `__file_write` writes at the current offset, so move it to
 *   the end of the file first. A write of 0 bytes leaves the offset unchanged
 *   (as on Linux). If `fd` may refer to several files, the size may be
 *   symbolic: fork once per feasible size, which `__file_set_offset` needs
 *   concrete.
 *
 * `count` must be concrete in `__file_write`: take its maximum and assume it.
 */
ssize_t summ_write(int fd, const void *buf, size_t count)
{
  int flags = __file_flags(fd);

  if (flags == -1 || (flags & O_ACCMODE) == O_RDONLY)
    return -1;

  size_t n = __maximize(count);
  __assume(_EQ_(count, n));

  if ((flags & O_APPEND) && n > 0)
  {
    ssize_t size = __file_size(fd);
    ssize_t end = __concretize(size);

    while (size != end)
      end = __concretize(size);

    __file_set_offset(fd, end);
  }

  return __file_write(fd, buf, n);
}
