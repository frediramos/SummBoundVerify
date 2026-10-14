#include "sra.h"

/*
 * Summary of: int dup2(int oldfd, int newfd)
 *
 * __file_dup2 does the work: it fails if oldfd is not open (EBADF, newfd
 * left untouched), does nothing if oldfd == newfd, closes newfd silently if
 * open, and fails for newfd past the descriptor limit (EBADF). oldfd may be
 * ite(cond, fd, -1) and is passed as is, so its failure case needs no branch.
 *
 * Branches:
 *  - newfd < 0 is out of range (EBADF). The API only bounds newfd from above,
 *    and no state changes on failure, so this returns -1 directly.
 *  - newfd must otherwise be concrete for the API, and each value closes and
 *    reuses a different descriptor, so a symbolic newfd forks once per
 *    possible value in [max(0, min), max].
 */
int dup2(int oldfd, int newfd)
{
    if (newfd < 0)
        return -1;

    if (!__is_symbolic(newfd))
        return __file_dup2(oldfd, newfd);

    int lo = __minimize(newfd);
    int hi = __maximize(newfd);
    if (lo < 0)
        lo = 0;

    for (int n = lo; n < hi; n++)
        if (newfd == n)
            return __file_dup2(oldfd, n);   // n is concrete here

    return __file_dup2(oldfd, hi);
}
