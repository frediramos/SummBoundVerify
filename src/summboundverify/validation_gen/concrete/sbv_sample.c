/*
 * The sampling harness -- see sbv_sample.h for what this is and is not.
 *
 * Record format, one block per test, on stdout:
 *
 *   V <name> <index|-> <bits> <hex>    one per drawn input
 *   M <name> <nbytes> <hex>            one per tagged region, contents after
 *   R <bits> <hex>                     absent for a void function
 *   E ok <test>                        closes the block and names it
 *
 * and, for a run the test's own assumptions turned away:
 *
 *   E rejected
 *
 * A block is named at the end rather than the start because the draws are
 * emitted as they happen, before the test that owns them is known to have
 * finished. The reader accumulates lines and closes on E.
 *
 * Bytes are hex in memory order, so the reader interprets them with the
 * target's endianness -- the same bytes the symbolic side sees, unconverted.
 * That matters for floating point, where any conversion would destroy the
 * bit pattern that is the value under test.
 */

#undef main

#include "sbv_sample.h"

#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The build redirects the target's exit() here with -Dexit=sbv_exit. This
 * file defines the stand-in, so it must see the name unredirected. */
#undef exit

#define SBV_MAX_REGIONS 16
#define SBV_MAX_REGION_LEN 4096
#define SBV_MAX_CHUNKS 64
#define SBV_NAME_LEN 64

/* Input tape ------------------------------------------------------------ */

static const unsigned char *g_input;
static size_t g_input_len;
static size_t g_input_pos;

static unsigned long g_total_execs;
static unsigned long g_total_rejected;
static unsigned long g_total_exited;

static int g_record;
static jmp_buf g_reject_jmp;

/*
 * One byte off the tape.
 *
 * Running off the end yields zeros rather than rejecting the run: AFL++ grows
 * an input only when the coverage it buys says to, so a short tape is the
 * normal case early on, and turning those runs away would starve the corpus
 * exactly when it is smallest.
 */
static unsigned char tape_byte(void)
{
    if (g_input_pos >= g_input_len)
        return 0;

    return g_input[g_input_pos++];
}

/* Copying without libc: a test's helper library may redirect memcpy, and the
 * harness must not go through whatever it redirected it to. */
static void sbv_memcpy(unsigned char *dst, const unsigned char *src, size_t n)
{
    size_t i;

    for (i = 0; i < n; i++)
        dst[i] = src[i];
}

static void sbv_strcpy(char *dst, size_t cap, const char *src)
{
    size_t i;

    for (i = 0; src && src[i] && i + 1 < cap; i++)
        dst[i] = src[i];

    dst[i] = '\0';
}

/* Tagged memory --------------------------------------------------------- */

typedef struct {
    char name[SBV_NAME_LEN];
    unsigned char *addr;
    size_t len;
} region_t;

static region_t g_regions[SBV_MAX_REGIONS];
static int g_nregions;

/* Emitting records ------------------------------------------------------ */

static void put_hex(const unsigned char *bytes, size_t n)
{
    static const char digits[] = "0123456789abcdef";
    size_t i;

    for (i = 0; i < n; i++) {
        putchar(digits[bytes[i] >> 4]);
        putchar(digits[bytes[i] & 0xf]);
    }
}

static void record_draw(const char *name, long index, int indexed,
                        const unsigned char *bytes, size_t bits)
{
    if (!g_record)
        return;

    printf("V %s ", name);

    if (indexed)
        printf("%ld ", index);
    else
        printf("- ");

    printf("%lu ", (unsigned long)bits);
    put_hex(bytes, (bits + 7) / 8);
    putchar('\n');
}

/* Drawing inputs -------------------------------------------------------- */

static void draw_bytes(char *name, unsigned char *dst, size_t bits,
                       long index, int indexed)
{
    size_t nbytes = (bits + 7) / 8;
    size_t i;

    for (i = 0; i < nbytes; i++)
        dst[i] = tape_byte();

    record_draw(name, index, indexed, dst, bits);
}

static sbv_value draw_value(char *name, size_t bits, long index, int indexed)
{
    unsigned char bytes[sizeof(sbv_value)];
    sbv_value value = 0;
    size_t nbytes = (bits + 7) / 8;
    size_t i;

    if (nbytes > sizeof(value))
        nbytes = sizeof(value);

    for (i = 0; i < sizeof(bytes); i++)
        bytes[i] = 0;

    for (i = 0; i < nbytes; i++)
        bytes[i] = tape_byte();

    /* Assemble little-endian, then hand back the value the test will store
     * into a possibly narrower variable. The record keeps the bytes, not the
     * assembled number, so the reader is not guessing at the width. */
    for (i = nbytes; i > 0; i--)
        value = (value << 8) | bytes[i - 1];

    record_draw(name, index, indexed, bytes, bits);
    return value;
}

sbv_value sym_var_named(char *name, size_t bits)
{
    return draw_value(name, bits, 0, 0);
}

sbv_value sym_var_array(char *name, size_t index, size_t bits)
{
    return draw_value(name, bits, (long)index, 1);
}

void sym_var_bytes(char *name, void *dst, size_t bits)
{
    draw_bytes(name, (unsigned char *)dst, bits, 0, 0);
}

/* Bounding the domain --------------------------------------------------- */

void assume(int cnstr)
{
    if (cnstr)
        return;

    g_total_rejected++;
    longjmp(g_reject_jmp, 1);
}

void _assert(int cnstr)
{
    assume(cnstr);
}

void sbv_exit(int code)
{
    (void)code;
    g_total_exited++;
    longjmp(g_reject_jmp, 1);
}

int _EQ_(sbv_value a, sbv_value b) { return a == b; }
int _NEQ_(sbv_value a, sbv_value b) { return a != b; }
int _LT_(sbv_value a, sbv_value b) { return a < b; }
int _LE_(sbv_value a, sbv_value b) { return a <= b; }
int _GT_(sbv_value a, sbv_value b) { return a > b; }
int _GE_(sbv_value a, sbv_value b) { return a >= b; }

int _ULT_(sbv_value a, sbv_value b)
{
    return (unsigned long)a < (unsigned long)b;
}

int _ULE_(sbv_value a, sbv_value b)
{
    return (unsigned long)a <= (unsigned long)b;
}

int _UGT_(sbv_value a, sbv_value b)
{
    return (unsigned long)a > (unsigned long)b;
}

int _UGE_(sbv_value a, sbv_value b)
{
    return (unsigned long)a >= (unsigned long)b;
}

int _NOT_(int c) { return !c; }
int _AND_(int a, int b) { return a && b; }
int _OR_(int a, int b) { return a || b; }

/* Heap ------------------------------------------------------------------ */

/* Sizes of the live allocations, so n_allocd() can answer. Freed slots are
 * reused; the table only has to outlive one execution. */
typedef struct {
    void *ptr;
    size_t size;
} chunk_t;

static chunk_t g_chunks[SBV_MAX_CHUNKS];

void *mem_alloc(size_t bytes)
{
    void *ptr = malloc(bytes);
    int i;

    if (ptr == NULL)
        return NULL;

    for (i = 0; i < SBV_MAX_CHUNKS; i++) {
        if (g_chunks[i].ptr == NULL) {
            g_chunks[i].ptr = ptr;
            g_chunks[i].size = bytes;
            break;
        }
    }

    return ptr;
}

void mem_free(void *ptr)
{
    int i;

    for (i = 0; i < SBV_MAX_CHUNKS; i++) {
        if (g_chunks[i].ptr == ptr) {
            g_chunks[i].ptr = NULL;
            g_chunks[i].size = 0;
            break;
        }
    }

    free(ptr);
}

size_t n_allocd(void *ptr)
{
    int i;

    for (i = 0; i < SBV_MAX_CHUNKS; i++)
        if (g_chunks[i].ptr == ptr)
            return g_chunks[i].size;

    return 0;
}

void allocd(void *ptr, size_t size)
{
    (void)size;
    assume(ptr != NULL);
}

/* Recording the outcome ------------------------------------------------- */

void mem_addr(char *name, void *addr, size_t len)
{
    region_t *r;

    if (g_nregions >= SBV_MAX_REGIONS)
        return;

    if (len > SBV_MAX_REGION_LEN)
        len = SBV_MAX_REGION_LEN;

    r = &g_regions[g_nregions++];
    sbv_strcpy(r->name, sizeof(r->name), name);
    r->addr = (unsigned char *)addr;
    r->len = len;
}

void sbv_record(char *test, void *ret, size_t bits)
{
    int i;

    if (!g_record) {
        g_nregions = 0;
        return;
    }

    for (i = 0; i < g_nregions; i++) {
        printf("M %s %lu ", g_regions[i].name,
               (unsigned long)g_regions[i].len);
        put_hex(g_regions[i].addr, g_regions[i].len);
        putchar('\n');
    }

    if (ret != 0 && bits != 0) {
        unsigned char bytes[sizeof(long double)];
        size_t nbytes = (bits + 7) / 8;

        if (nbytes > sizeof(bytes))
            nbytes = sizeof(bytes);

        sbv_memcpy(bytes, (const unsigned char *)ret, nbytes);

        printf("R %lu ", (unsigned long)bits);
        put_hex(bytes, nbytes);
        putchar('\n');
    }

    printf("E ok %s\n", test);
    g_nregions = 0;
}

/* Driver interface ------------------------------------------------------ */

static void reset(const unsigned char *data, size_t len, int record)
{
    g_input = data;
    g_input_len = len;
    g_input_pos = 0;

    g_nregions = 0;
    g_record = record;
}

int sbv_sample_exec(const unsigned char *data, size_t len,
                    int (*tests)(void), int record)
{
    reset(data, len, record);
    g_total_execs++;

    if (setjmp(g_reject_jmp) != 0) {
        if (record)
            printf("E rejected\n");
        return SBV_REJECTED;
    }

    tests();
    return SBV_OK;
}

unsigned long sbv_sample_total_execs(void)
{
    return g_total_execs;
}

unsigned long sbv_sample_total_rejected(void)
{
    return g_total_rejected;
}

unsigned long sbv_sample_total_exited(void)
{
    return g_total_exited;
}
