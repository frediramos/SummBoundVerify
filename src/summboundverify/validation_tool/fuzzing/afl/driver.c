/*
 * AFL++ persistent-mode driver for the sampling harness.
 *
 * The fuzzer's job here is not to find anything. It is to *generate inputs*:
 * coverage-guided search over the concrete function, whose queue ends up
 * holding a small, deduplicated set of tapes that between them reach the
 * function's distinct behaviours. Checking those samples against the summary
 * happens later, and elsewhere -- in angr, against the formula the summary's
 * symbolic run produced.
 *
 * So the loop below has no oracle and never abort()s on a finding. Two modes:
 *
 *   (default)         run the tape, emit nothing. This is the exploration
 *                     pass; recording every one of tens of thousands of
 *                     executions would cost far more than it is worth when
 *                     AFL++ is about to throw nearly all of them away.
 *
 *   --record <tape>   run one saved tape and print its sample. This is the
 *                     pass that matters, run over the queue AFL++ built.
 *
 * The generated test's main() is renamed to sbv_run_tests by the compiler
 * (-Dmain=sbv_run_tests), so this file can own the real main(). Undo that
 * define here, before anything else.
 */

#undef main

/* The driver owns the real exit(), not the target's stand-in. */
#undef exit

#include "sbv_sample.h"

#include <stdio.h>
#include <stdlib.h>
/* __AFL_FUZZ_TESTCASE_LEN expands to a read(2) call. */
#include <unistd.h>
#include <fcntl.h>

#define MAX_TAPE 65536

/* Iterations per forked process. The harness resets its own state per exec,
 * so this is bounded only by what the concrete function itself might leak. */
#define PERSISTENT_LOOP 1000

int sbv_run_tests(void);

/* Not strcmp(): a concrete function may be named strcmp and would override
 * libc's. */
static int arg_is(const char *arg, const char *want) {
    size_t i;

    for (i = 0; arg[i] || want[i]; i++)
        if (arg[i] != want[i])
            return 0;

    return 1;
}

__AFL_FUZZ_INIT();

/*
 * Run a single saved tape outside AFL++ and print what the concrete function
 * did with it.
 */
static int record(const char *path) {
    static unsigned char buf[MAX_TAPE];
    ssize_t len;
    int fd;

    /*
     * open/read rather than fopen/fread: a test's helper library may redirect
     * malloc (tests/libc/synth/exact/strdup/lib.c does), and stdio would then
     * allocate its buffer from wherever that points while releasing it to
     * glibc. Anything in this process that allocates through libc is unsafe
     * for the same reason.
     */
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "record: cannot open %s\n", path);
        return 2;
    }

    len = read(fd, buf, sizeof(buf));
    close(fd);

    if (len < 0)
        len = 0;

    sbv_sample_exec(buf, (size_t)len, sbv_run_tests, 1);
    return 0;
}

/* Dump totals where the engine can find them; the persistent loop means the
 * process may be restarted many times, so last writer wins.
 *
 * open/write rather than fopen/fprintf, for the same reason record() reads
 * that way: stdio allocates its buffer through malloc, a target's helper
 * library may have routed malloc to mem_alloc, and fclose would then hand an
 * arena pointer to glibc's free(). That aborts with "free(): invalid
 * pointer" -- at exit, where AFL++ reads it as a crash. */
static void write_stats(void) {
    const char *path = getenv("SBV_STATS_FILE");
    char line[128];
    int fd, n;

    if (!path)
        return;

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0)
        return;

    n = snprintf(line, sizeof(line), "execs=%lu rejected=%lu exited=%lu\n",
                 sbv_sample_total_execs(), sbv_sample_total_rejected(),
                 sbv_sample_total_exited());

    if (n > 0)
        (void)!write(fd, line, (size_t)n);

    close(fd);
}

int main(int argc, char **argv) {
    unsigned char *buf;

    /* Unbuffered: stdio would otherwise malloc() its buffer, which may come
     * from wherever the test redirected allocation. See record(). */
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (argc == 3 && arg_is(argv[1], "--record"))
        return record(argv[2]);

    atexit(write_stats);

    __AFL_INIT();
    buf = __AFL_FUZZ_TESTCASE_BUF;

    while (__AFL_LOOP(PERSISTENT_LOOP)) {
        int len = __AFL_FUZZ_TESTCASE_LEN;

        /* A rejected tape is not a finding -- it is simply outside the
         * test's domain. Keep going; AFL++ learns which bytes matter. */
        sbv_sample_exec(buf, (size_t)len, sbv_run_tests, 0);
    }

    return 0;
}
