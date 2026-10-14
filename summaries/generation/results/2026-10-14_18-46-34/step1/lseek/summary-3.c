#include "sra.h"

#define SEEK_SET  0
#define SEEK_CUR  1
#define SEEK_END  2
#define SEEK_DATA 3
#define SEEK_HOLE 4

#define MAX_FORKS 64

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
 * `__file_set_offset` needs a concrete position, and the descriptor's offset
 * stays concrete, so every possible position needs its own path. Where the
 * descriptor is open (`__file_flags` is not -1), the position's range is
 * measured:
 *  - at most MAX_FORKS + 1 values: one path per value, which is exact.
 *  - more: the position is concretized once and constrained to that value.
 *    This drops every other position; the API cannot express them.
 * Where the descriptor is not open the result is -1 whatever the offset, so
 * the range ignores it, and the concretization does not constrain it.
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

    if (!__is_symbolic(pos))
        return __file_set_offset(fd, pos);

    cnstr_t closed = _EQ_(__file_flags(fd), -1);
    if (!__is_sat(_NOT_(closed)))
        return -1;

    // The positions an open descriptor can reach
    __push_pc();
    __assume(_NOT_(closed));
    off_t min = __minimize(pos);
    off_t max = __maximize(pos);
    __pop_pc();

    if (max - min <= MAX_FORKS) {
        for (off_t n = min; n < max; n++)
            if (pos == n)
                return __file_set_offset(fd, n);
        return __file_set_offset(fd, max);
    }

    off_t c = __concretize(pos);
    __assume(_OR_(closed, _EQ_(pos, c)));
    return __file_set_offset(fd, c);
}
