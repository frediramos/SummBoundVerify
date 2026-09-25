/*
 * Undo the build's redirections.
 *
 * The harness is compiled with -Dmain=sbv_run_tests, -Dexit=sbv_exit and
 * -Dopen=sbv_open etc. (see _cflags() in engine.py, which this list must
 * match), so that the generated test and the concrete function reach the
 * harness's stand-ins. The harness itself needs the real functions: the
 * wrappers call them, and the driver's own file I/O must not be tracked.
 *
 * Included first by sbv_sample.c and driver.c. Without it, every wrapper
 * would call itself.
 */

#undef main
#undef exit

#undef open
#undef creat
#undef openat
#undef dup
#undef dup2
#undef close
#undef fclose
