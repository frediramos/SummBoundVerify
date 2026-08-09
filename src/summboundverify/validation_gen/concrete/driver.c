/*
 * AFL++ persistent-mode driver for the concrete backend.
 *
 * This is the only driver: coverage feedback is not optional here. The
 * generated tests constrain their inputs (`assume(_ULE_(n, MAX_NUM_1))`), and
 * a driver that cannot learn which bytes matter is rejected on nearly every
 * input -- an earlier PRNG loop was turned away on 87% of them where AFL++
 * gets that down to under 60%.
 *
 * The generated test's main() is renamed to sbv_run_tests by the compiler
 * (-Dmain=sbv_run_tests), so this file can own the real main(). Undo that
 * define here, before anything else.
 *
 * AFL++ hands us a byte tape in shared memory, which is exactly what
 * sbv_fuzz_exec() consumes -- so the runtime is unchanged between this driver
 * and the random one. What AFL++ adds is coverage-guided search: it learns
 * which bytes matter, which matters a great deal here because the generated
 * tests constrain their inputs (`assume(_ULE_(n, MAX_NUM_1))`) and a blind
 * driver spends nearly all its budget getting rejected.
 *
 * A divergence is reported by abort()ing, so AFL++ records the tape that
 * produced it under `crashes/`. The engine then re-runs that tape through
 * --replay to recover the decoded counterexample.
 */

#undef main

/* The driver owns the real exit(), not the target's stand-in. */
#undef exit

#include "sbv_runtime.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* __AFL_FUZZ_TESTCASE_LEN expands to a read(2) call. */
#include <unistd.h>
#include <fcntl.h>

#define MAX_REPLAY 65536

/* Iterations per forked process. Higher is faster but leaks more state
 * between runs; the runtime resets its own state per exec, so this is only
 * bounded by what the summary itself might leak (e.g. the heap). */
#define PERSISTENT_LOOP 1000

int sbv_run_tests(void);

/* Not strcmp(): a summary may be named strcmp and would override libc's. */
static int arg_is(const char *arg, const char *want)
{
    size_t i;

    for (i = 0; arg[i] || want[i]; i++)
        if (arg[i] != want[i])
            return 0;

    return 1;
}

__AFL_FUZZ_INIT();

static void report(int rc)
{
    printf("SBV_FUZZ execs=%lu rejected=%lu ntests=%d verdict=%s",
           sbv_fuzz_total_execs(), sbv_fuzz_total_rejected(),
           sbv_fuzz_ntests() > 0 ? sbv_fuzz_ntests() : 1,
           rc == SBV_DIVERGED ? "diverged"
               : (rc == SBV_REJECTED ? "rejected" : "passed"));

    if (rc == SBV_DIVERGED)
        printf(" test=%d inputs=%s report=%s", sbv_fuzz_diverged_test(),
               sbv_fuzz_inputs(), sbv_fuzz_report());

    printf("\n");
}

/*
 * Re-run a single saved tape outside AFL++, to turn a crashing input into a
 * readable counterexample.
 */
static int replay(const char *path)
{
    static unsigned char buf[MAX_REPLAY];
    ssize_t len;
    int fd, rc;

    /*
     * open/read rather than fopen/fread: a test's helper library may route
     * malloc() to mem_alloc() (tests/libc/synth/exact/strdup/lib.c does), and
     * then stdio's internal buffer is allocated from the runtime's arena but
     * released with glibc's free() -- "free(): invalid pointer". Anything in
     * this process that allocates through libc is unsafe for the same reason.
     */
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "replay: cannot open %s\n", path);
        return 2;
    }

    len = read(fd, buf, sizeof(buf));
    close(fd);

    if (len < 0)
        len = 0;

    rc = sbv_fuzz_exec(buf, (size_t)len, sbv_run_tests);
    report(rc);
    return 0;
}

/* Dump totals where the engine can find them; the persistent loop means the
 * process may be restarted many times, so last writer wins. */
static void write_stats(void)
{
    const char *path = getenv("SBV_STATS_FILE");
    FILE *f;

    if (!path)
        return;

    f = fopen(path, "w");
    if (!f)
        return;

    fprintf(f, "execs=%lu rejected=%lu exited=%lu ntests=%d\n",
            sbv_fuzz_total_execs(), sbv_fuzz_total_rejected(),
            sbv_fuzz_total_exited(),
            sbv_fuzz_ntests() > 0 ? sbv_fuzz_ntests() : 1);
    fclose(f);
}

int main(int argc, char **argv)
{
    unsigned char *buf;

    /* Unbuffered: stdio would otherwise malloc() its buffer, which may come
     * from the runtime's arena and be freed by glibc. See replay(). */
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (argc == 3 && arg_is(argv[1], "--replay"))
        return replay(argv[2]);

    atexit(write_stats);

    __AFL_INIT();
    buf = __AFL_FUZZ_TESTCASE_BUF;

    while (__AFL_LOOP(PERSISTENT_LOOP)) {
        int len = __AFL_FUZZ_TESTCASE_LEN;
        int rc = sbv_fuzz_exec(buf, (size_t)len, sbv_run_tests);

        if (rc == SBV_DIVERGED) {
            /* Print before aborting: the stderr text lands in AFL++'s logs,
             * and the tape itself is saved under crashes/ for --replay. */
            fprintf(stderr, "SBV_DIVERGED test=%d inputs=%s report=%s\n",
                    sbv_fuzz_diverged_test(), sbv_fuzz_inputs(),
                    sbv_fuzz_report());
            write_stats();
            abort();
        }

        /* SBV_REJECTED and SBV_OK both continue: a rejected input is simply
         * outside the summary's domain, not a finding. */
    }

    return 0;
}
