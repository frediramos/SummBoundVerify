typedef unsigned int size_t;
typedef int ssize_t;

/*
 * Summary of: ssize_t write(int fd, const void *buf, size_t count)
 *
 * `fd` may be `ite(cond, fd, -1)`: `__file_write` applies the write to `fd`
 * and returns `ite(cond, count, -1)`, so the failure case needs no branch.
 *
 * `count` must be concrete in `__file_write`. When it is symbolic, fork on it
 * natively, so that each path writes a single concrete count.
 */
ssize_t summ_write(int fd, const void *buf, size_t count)
{
  if (!__is_symbolic(count))
    return __file_write(fd, buf, count);

  size_t max = __maximize(count);

  for (size_t n = 0; n < max; n++)
  {
    if (count == n)
      return __file_write(fd, buf, n);
  }

  return __file_write(fd, buf, max);
}
