#include "sra.h"

#define SEEK_SET  0
#define SEEK_CUR  1
#define SEEK_END  2
#define SEEK_DATA 3
#define SEEK_HOLE 4

/*
 * Summary of: off_t lseek(int fd, off_t offset, int whence)
 *
 * Branches:
 *  - whence: one path per directive, as each computes the position from a
 *    different base; any other value fails (EINVAL).
 *  - SEEK_DATA / SEEK_HOLE: fail unless 0 <= offset < size (ENXIO). The file
 *    is modelled with no holes but the implicit one at its end, so SEEK_DATA
 *    stays at offset and SEEK_HOLE moves to the size, as the man page allows.
 *    The bounds are combined with `|` so that they form a single branch.
 *  - pos < 0: fails (EINVAL). With a 32-bit off_t, base is in [0, INT_MAX],
 *    so a sum past INT_MAX wraps to a negative value: the same branch also
 *    covers EOVERFLOW.
 *
 * No branch for a bad descriptor (EBADF): `__file_offset` and `__file_size`
 * then return -1, and `__file_set_offset` fails with -1 whatever position it
 * gets. A descriptor `ite(cond, fd, -1)` is passed as is, so its failure case
 * is folded into the result `ite(cond, pos, -1)`.
 *
 * `__file_set_offset` needs a concrete position: `offset` is unbounded, so
 * the position is concretized once and constrained to the chosen value. The
 * constraint only applies where the descriptor is open (`__file_flags` is not
 * -1): elsewhere the result is -1 whatever the offset, so it is left free
 * there, without forking on the descriptor.
 */
off_t lseek(int fd, off_t offset, int whence)
{
    off_t pos;

    if (whence == SEEK_SET)
        pos = offset;
    else if (whence == SEEK_CUR)
        pos = __file_offset(fd) + offset;
    else if (whence == SEEK_END)
        pos = __file_size(fd) + offset;
    else if (whence == SEEK_DATA || whence == SEEK_HOLE) {
        off_t size = __file_size(fd);
        if ((offset < 0) | (offset >= size))
            return -1;
        pos = (whence == SEEK_DATA) ? offset : size;
    }
    else
        return -1;

    if (pos < 0)
        return -1;

    if (__is_symbolic(pos)) {
        int flags = __file_flags(fd);
        off_t c = __concretize(pos);
        __assume(_OR_(_EQ_(flags, -1), _EQ_(pos, c)));
        pos = c;
    }

    return __file_set_offset(fd, pos);
}
