Write a summary of the libc function `{{function}}`. Its manual page is `{{man_page}}`.

Previous summaries can be found in `{{examples}}`, and summarization templates in `{{templates}}`. The Symbolic Reflection API that a summary may use is documented in `src/summboundverify/api/sra.h`. A summary aims to minimise branching when possible.

The summary includes the API's header, `#include "sra.h"`, which also declares the libc types. To compile it yourself: `gcc -m32 -Wno-int-conversion -c -I tests/files/testsuite/lib {{output}} -o /dev/null`.

Write the summary to `{{output}}`, as a C function named `{{summname}}` with
the same signature as `{{function}}`.
