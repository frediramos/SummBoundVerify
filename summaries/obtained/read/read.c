/*Summary for libc's read*/

#include "sra.h"

#define O_ACCMODE    0003
#define O_WRONLY     1

#define MAX_RW_COUNT 0x7ffff000

/*
 * Summary of: ssize_t read(int fd, void *buf, size_t count)
 *
 * The descriptor may be ite(cond, fd, -1). Its -1 case, and a descriptor that
 * is not open, already make __file_read fail, so they need no branch.
 *
 * The API reads from write-only descriptors, so the access mode is checked
 * (EBADF), before the count as Linux does. Being certain of failure covers
 * both cases of ite(cond, fd, -1) without forking: the -1 case always fails,
 * and the open case's flags are concrete.
 *
 * Linux transfers at most MAX_RW_COUNT bytes per call.
 *
 * __file_read needs a concrete count. A symbolic count forks once per value
 * still reading less than what is left before the end of the file: every
 * larger count reads the same bytes, so its maximum covers them all.
 *
 * EFAULT, EISDIR and the device-specific errors cannot be modelled.
 */
ssize_t read(int fd, void *buf, size_t count)
{
	int flags = __file_flags(fd);

	if (__is_certain(_OR_(_EQ_(flags, -1), _EQ_(flags & O_ACCMODE, O_WRONLY))))
		return -1;

	if (!__is_symbolic(count)) {
		if (count > MAX_RW_COUNT)
			count = MAX_RW_COUNT;
		return __file_read(fd, buf, count);
	}

	// Bytes left before the end of the file (0 when fd is -1, <= 0 past EOF)
	ssize_t left = __file_size(fd) - __file_offset(fd);

	size_t max = __maximize(count);
	if (max > MAX_RW_COUNT)
		max = MAX_RW_COUNT;

	for (size_t n = __minimize(count); n < max; n++) {
		// From here on every count reads all that is left
		if (__is_certain(_GE_(n, left)))
			break;
		if (count == n)
			return __file_read(fd, buf, n);    // n is concrete here
	}

	return __file_read(fd, buf, max);
}
