#include "sra.h"

#define S_IALLUGO 07777

/*
 * Summary of: int chmod(const char *pathname, mode_t mode)
 *
 * The file is reached through a descriptor, since the API sets modes on
 * descriptors only. A NULL pathname fails (EFAULT). `__file_set_mode` needs
 * a concrete mode, so a symbolic one is concretized. Only the mode bits
 * (permissions, set-user-ID, set-group-ID, sticky) are kept.
 *
 * No other branch is needed: a missing file or an invalid name makes
 * `__file_open` return -1 (or ite(valid, fd, -1) for a symbolic name), on
 * which `__file_set_mode` and `__file_close` fail as well. The result of
 * `__file_close` is then exactly chmod's: 0 on success, -1 on failure (ENOENT).
 */
int chmod(const char *pathname, mode_t mode)
{
    // EFAULT
    if (pathname == NULL)
        return -1;

    // The API needs a concrete mode
    if (__is_symbolic(mode)) {
        mode_t m = __concretize(mode);
        __assume(_EQ_(mode, m));
        mode = m;
    }

    int fd = __file_open(pathname, "r");
    __file_set_mode(fd, mode & S_IALLUGO);

    return __file_close(fd);
}
