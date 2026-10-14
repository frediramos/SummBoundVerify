#include "sra.h"

/*
 * Summary of: int dup(int oldfd)
 *
 * No branch is needed: `__file_dup` already returns a new descriptor
 * sharing the offset, mode and flags of `oldfd`, and fails
 * with -1 both when `oldfd` is not open (EBADF) and when the descriptor
 * limit is reached (EMFILE). A descriptor of the form `ite(cond, fd, -1)`
 * is passed as is, giving `ite(cond, <new fd>, -1)`. The close-on-exec
 * flag of the new descriptor is off, which the API does not model.
 */
int dup(int oldfd)
{
    return __file_dup(oldfd);
}
