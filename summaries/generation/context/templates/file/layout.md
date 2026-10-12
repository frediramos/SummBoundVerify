The layout of a summary file. Include `sra.h`, the API's header: it declares the API's functions and the libc types (`size_t`, `ssize_t`, `mode_t`, `off_t`), so the summary declares no types of its own. Define only the constants it uses. Name the function after the libc function, and explain each branch in its comment.

```c
#include "sra.h"

#define O_ACCMODE 0003

/*
 * Summary of: ssize_t read(int fd, void *buf, size_t count)
 *
 * Why each branch is there, and why the rest needs none.
 */
ssize_t read(int fd, void *buf, size_t count)
{
    ...
}
```
