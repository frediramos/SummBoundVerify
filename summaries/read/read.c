typedef unsigned int size_t;
typedef int ssize_t;

/*
 * Summary of: ssize_t read(int fd, void *buf, size_t count)
 *
 * `fd` may be `ite(cond, fd, -1)`: `__file_read` applies the read to `fd`
 * and returns `ite(cond, nread, -1)`, so the failure case needs no branch.
 *
 * `count` must be concrete in `__file_read`. When it is symbolic, fork on it
 * natively, so that each path reads a single concrete count.
 */
ssize_t summ_read(int fd, void *buf, size_t count)
{
  if (!__is_symbolic(count))
    return __file_read(fd, buf, count);

  size_t max = __maximize(count);

  for (size_t n = 0; n < max; n++)
  {
    if (count == n)
      return __file_read(fd, buf, n);
  }

  return __file_read(fd, buf, max);
}
