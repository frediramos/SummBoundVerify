#include "sra.h"

/*
 * Summary of: int close(int fd)
 *
 * No branches are needed. A descriptor that is not open (EBADF), including a
 * negative one, makes `__file_close` fail with -1. A descriptor from a
 * symbolic name, `ite(cond, fd, -1)`, is passed as is: the result is
 * `ite(cond, 0, -1)`, so its failure case needs no branch either. EINTR,
 * EIO, ENOSPC and EDQUOT come from signals and the underlying storage, which
 * the model does not have.
 */
int close(int fd)
{
    return __file_close(fd);
}
