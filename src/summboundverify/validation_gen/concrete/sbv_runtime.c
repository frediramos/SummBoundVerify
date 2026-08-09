/*
 * Concrete backend for the SummBoundVerify API. See sbv_runtime.h.
 *
 * Why this is only ~a few hundred lines: with fully concrete inputs the
 * solver-facing half of the API collapses. `is_certain(c)` is
 * `not satisfiable(Not(c))`, which for a concrete `c` is just `c`; so the
 * multi-path arm of every generated summary (push_pc / pop_pc / _ITE_VAR_
 * merge) is unreachable, and the path condition stays trivially true.
 */

#include "sbv_runtime.h"

#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SBV_MAX_REGIONS 8
#define SBV_MAX_REGION_LEN 4096
#define SBV_MAX_SNAPSHOTS 8
#define SBV_MAX_NAMES 8
#define SBV_MAX_RET 16

#define SBV_MAX_LISTS 8192
#define SBV_MAX_LIST_LEN 512

#define SBV_MAX_CHUNKS 64
#define SBV_ARENA_SIZE (1u << 20)
#define SBV_REPORT_LEN 512
#define SBV_MAX_DRAWS 64
#define SBV_MAX_STREAMS 4
#define SBV_MAX_STREAM_LEN 256
#define SBV_INPUTS_LEN 1024

/* ------------------------------------------------------------------ */
/* Input tape                                                          */
/* ------------------------------------------------------------------ */

static const unsigned char *g_input;
static size_t g_input_len;
static size_t g_input_pos;

/*
 * Draw the next `size` bits from the input tape. Running off the end yields
 * zeroes rather than failing: the generated test consumes a fixed amount per
 * run (bounded by ARRAY_SIZE_n), so a short tape should still produce a
 * valid, if boring, input.
 */
static long tape_next(size_t size)
{
    size_t nbytes = size / 8;
    unsigned long value = 0;
    size_t i;

    if (nbytes == 0 || nbytes > sizeof(unsigned long))
        nbytes = sizeof(unsigned long);

    for (i = 0; i < nbytes; i++) {
        unsigned char byte = 0;
        if (g_input_pos < g_input_len)
            byte = g_input[g_input_pos];
        g_input_pos++;
        value |= ((unsigned long)byte) << (8 * i);
    }

    /* Sign-extend so that a drawn `char` compares the way the C code that
     * consumes it would compare it. */
    if (nbytes < sizeof(unsigned long)) {
        unsigned long sign_bit = 1UL << (8 * nbytes - 1);
        if (value & sign_bit)
            value |= ~((1UL << (8 * nbytes)) - 1);
    }

    return (long)value;
}

/* ------------------------------------------------------------------ */
/* Run state                                                           */
/* ------------------------------------------------------------------ */

typedef struct {
    char name[64];
    unsigned char *addr;
    size_t len;
    unsigned char orig[SBV_MAX_REGION_LEN];
} region_t;

typedef struct {
    int used;
    unsigned char ret[SBV_MAX_RET];
    size_t ret_len;
    int nregions;
    unsigned char mem[SBV_MAX_REGIONS][SBV_MAX_REGION_LEN];
    size_t mem_len[SBV_MAX_REGIONS];
} snapshot_t;

typedef struct {
    char name[64];
    cnstr_t handle;
    int used;
} binding_t;

static region_t g_regions[SBV_MAX_REGIONS];

/* A stream argument: the bytes drawn for it, and the FILE* handed to the
 * function under test. The buffer must outlive the FILE*, hence the table. */
typedef struct {
    char name[64];
    unsigned char data[SBV_MAX_STREAM_LEN];
    size_t len;
    FILE *fp;
} stream_t;

static stream_t g_streams[SBV_MAX_STREAMS];
static int g_nstreams;
static int g_nregions;

static snapshot_t g_snapshots[SBV_MAX_SNAPSHOTS];
static int g_nsnapshots;

static binding_t g_bindings[SBV_MAX_NAMES];
static int g_nbindings;

/* One entry per named draw from the input tape, for decoded reporting. */
typedef struct {
    char name[32];
    long index;
    int indexed;
    long value;
    size_t bits;

    /* Draws made through sym_var_bytes() carry their bytes verbatim: the
     * value may be wider than a long (a double at -m32) or not an integer at
     * all, so `value` cannot represent it. */
    int raw;
    unsigned char bytes[8];
} draw_t;

static draw_t g_draws[SBV_MAX_DRAWS];
static int g_ndraws;
static char g_inputs[SBV_INPUTS_LEN];

/* Persistent across runs: a single process performs many runs under AFL++. */
static unsigned long g_total_execs;
static unsigned long g_total_rejected;

static jmp_buf g_reject_jmp;
static int g_rejected;
static int g_diverged_test;
static int g_ntests;
static char g_report[SBV_REPORT_LEN];

/* Lists are a handle table, mirroring ctx.LIST_MAP in the symbolic backend. */
typedef struct {
    long items[SBV_MAX_LIST_LEN];
    int len;
} sbv_list;

static sbv_list g_lists[SBV_MAX_LISTS];
static int g_nlists;

/* Heap chunks, mirroring ctx.HEAP_CHUNKS. */
typedef struct {
    void *ptr;
    size_t size;
} chunk_t;

static chunk_t g_chunks[SBV_MAX_CHUNKS];
static int g_nchunks;

/*
 * Private arena for mem_alloc().
 *
 * malloc() is not usable here: `tests/libc/synth/exact/strdup/lib.c` defines
 *
 *     void *malloc(size_t size) { return mem_alloc(size); }
 *
 * which overrides libc's allocator for the whole program, so a mem_alloc()
 * implemented on top of malloc() recurses until the stack overflows. Routing
 * libc names onto the API is a deliberate pattern in the test suite, so the
 * runtime allocates from its own storage instead.
 *
 * A bump allocator also suits the workload: every exec resets, so mem_free()
 * need not reclaim anything and a longjmp out of assume() leaks nothing.
 */
static unsigned char g_arena[SBV_ARENA_SIZE];
static size_t g_arena_off;

/*
 * Private mem/str helpers.
 *
 * The summary under test is linked into this binary and may be named after a
 * libc function -- `memcpy`, `strlen` and `strcasecmp` are all in the test
 * suite. Its definition then overrides libc's for the whole program, so any
 * libc call the *runtime* makes would be routed through the function under
 * test. That silently corrupts the snapshots: with a faulty summary the diff
 * is garbage, and with a correct one both sides are corrupted identically and
 * the comparison reports a false pass.
 *
 * So the runtime calls none of them.
 */

static void sbv_memcpy(void *dst, const void *src, size_t n)
{
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    size_t i;

    for (i = 0; i < n; i++)
        d[i] = s[i];
}

static int sbv_memcmp(const void *a, const void *b, size_t n)
{
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    size_t i;

    for (i = 0; i < n; i++)
        if (x[i] != y[i])
            return x[i] < y[i] ? -1 : 1;

    return 0;
}

static int sbv_streq(const char *a, const char *b)
{
    size_t i;

    for (i = 0; a[i] || b[i]; i++)
        if (a[i] != b[i])
            return 0;

    return 1;
}

/* Bounded copy; always NUL-terminates. */
static void sbv_strcpy(char *dst, size_t dstlen, const char *src)
{
    size_t i;

    if (!dstlen)
        return;

    if (!src)
        src = "?";

    for (i = 0; i + 1 < dstlen && src[i]; i++)
        dst[i] = src[i];

    dst[i] = '\0';
}

/* Append the hex encoding of `n` bytes; returns the new offset. */
static size_t sbv_hex(char *dst, size_t dstlen, size_t off,
                      const unsigned char *src, size_t n)
{
    static const char digits[] = "0123456789abcdef";
    size_t i;

    for (i = 0; i < n && off + 2 < dstlen; i++) {
        dst[off++] = digits[(src[i] >> 4) & 0xf];
        dst[off++] = digits[src[i] & 0xf];
    }

    dst[off] = '\0';
    return off;
}

static void fail(const char *msg)
{
    fprintf(stderr, "sbv_runtime: %s\n", msg);
    abort();
}

/* ------------------------------------------------------------------ */
/* Core primitives                                                     */
/* ------------------------------------------------------------------ */

static long record(const char *name, long index, int indexed, size_t bits)
{
    long value = tape_next(bits);
    draw_t *d;

    if (g_ndraws >= SBV_MAX_DRAWS)
        return value;

    d = &g_draws[g_ndraws++];
    sbv_strcpy(d->name, sizeof(d->name), name);
    d->index = index;
    d->indexed = indexed;
    d->value = value;
    d->bits = bits;
    d->raw = 0;
    return value;
}

static unsigned char tape_byte(void)
{
    unsigned char byte = 0;

    if (g_input_pos < g_input_len)
        byte = g_input[g_input_pos];

    g_input_pos++;
    return byte;
}

/*
 * Whether a diverging return should be shown as a float.
 *
 * The runtime is not told the return type, so this infers it: the test drew a
 * floating-point argument through sym_var_bytes(), and the returns are of
 * float width. A function taking a double and returning a long long would be
 * rendered wrongly, which is why this is only a display choice -- the
 * comparison itself never looks at it.
 */
static int returns_float(const snapshot_t *a, const snapshot_t *b)
{
    int i;

    if (a->ret_len != b->ret_len)
        return 0;

    if (a->ret_len != sizeof(float) && a->ret_len != sizeof(double))
        return 0;

    for (i = 0; i < g_ndraws; i++)
        if (g_draws[i].raw)
            return 1;

    return 0;
}

static void render_float(char *out, size_t cap, const unsigned char *bytes,
                         size_t len)
{
    if (len == sizeof(float)) {
        float f;
        sbv_memcpy((unsigned char *)&f, bytes, sizeof(f));
        snprintf(out, cap, "%g", (double)f);
    } else {
        double d;
        sbv_memcpy((unsigned char *)&d, bytes, sizeof(d));
        snprintf(out, cap, "%g", d);
    }
}

FILE *sym_var_stream(char *name, size_t len)
{
    stream_t *st;
    size_t i;

    if (g_nstreams >= SBV_MAX_STREAMS)
        fail("too many stream arguments");

    if (len > SBV_MAX_STREAM_LEN)
        len = SBV_MAX_STREAM_LEN;

    st = &g_streams[g_nstreams];
    sbv_strcpy(st->name, sizeof(st->name), name);
    st->len = len;

    for (i = 0; i < len; i++)
        st->data[i] = tape_byte();

    st->fp = fmemopen(st->data, len, "r");
    if (st->fp == NULL)
        fail("fmemopen failed for a stream argument");

    g_nstreams++;

    /* Recorded as an array so a counterexample reads str[0]=0x61 ... the way
     * a char* argument does; the bytes are what the caller needs to see. */
    for (i = 0; i < len && g_ndraws < SBV_MAX_DRAWS; i++) {
        draw_t *d = &g_draws[g_ndraws++];
        sbv_strcpy(d->name, sizeof(d->name), name);
        d->index = (long)i;
        d->indexed = 1;
        d->value = st->data[i];
        d->bits = 8;
        d->raw = 0;
    }

    return st->fp;
}

void sym_var_bytes(char *name, void *dst, size_t bits)
{
    unsigned char *out = (unsigned char *)dst;
    size_t nbytes = bits / 8;
    draw_t *d;
    size_t i;

    if (nbytes == 0)
        return;

    /* Byte-wise rather than through record()/tape_next(), which funnel every
     * draw through a `long` -- 4 bytes at -m32, so a double would silently
     * lose half of its bits. */
    for (i = 0; i < nbytes; i++)
        out[i] = tape_byte();

    if (g_ndraws >= SBV_MAX_DRAWS)
        return;

    d = &g_draws[g_ndraws++];
    sbv_strcpy(d->name, sizeof(d->name), name);
    d->index = 0;
    d->indexed = 0;
    d->value = 0;
    d->bits = bits;
    d->raw = 1;

    for (i = 0; i < nbytes && i < sizeof(d->bytes); i++)
        d->bytes[i] = out[i];
}

symbolic sym_var(size_t size)
{
    /*
     * The symbolic backend returns a *fresh unconstrained* variable here.
     * There is no concrete counterpart, so we draw from the input tape: the
     * fuzzer picks the value, and any assume() that follows acts as
     * rejection sampling over that choice. This makes a nondeterministic
     * summary testable, but only samples its output set -- it cannot show
     * that every draw is admissible.
     */
    return record("<fresh>", 0, 0, size);
}

symbolic sym_var_named(char *name, size_t size)
{
    return record(name, 0, 0, size);
}

symbolic sym_var_array(char *name, size_t index, size_t size)
{
    return record(name, (long)index, 1, size);
}

int is_symbolic(symbolic var)
{
    (void)var;
    return 0;
}

int is_sat(cnstr_t cnstr)
{
    return cnstr != 0;
}

int is_certain(cnstr_t cnstr)
{
    return cnstr != 0;
}

void assume(cnstr_t cnstr)
{
    /*
     * The symbolic backend raises UnsatConstraintError when the assumption
     * contradicts the path condition. Concretely that is exactly rejection
     * sampling: this input does not belong to the summary's domain, so
     * abandon the run rather than reporting a divergence.
     */
    if (!cnstr) {
        g_rejected = 1;
        longjmp(g_reject_jmp, 1);
    }
}

void _assert(int expr)
{
    if (!expr) {
        g_rejected = 1;
        longjmp(g_reject_jmp, 1);
    }
}

void push_pc(void)
{
    /* No-op: with concrete inputs the path condition is trivially true. */
}

void pop_pc(void)
{
}

long maximize(symbolic var)
{
    return var;
}

long minimize(symbolic var)
{
    return var;
}

/* ------------------------------------------------------------------ */
/* Constraints                                                         */
/* ------------------------------------------------------------------ */

cnstr_t _NOT_(cnstr_t cnstr) { return !cnstr; }
cnstr_t _OR_(cnstr_t a, cnstr_t b) { return (a != 0) || (b != 0); }
cnstr_t _AND_(cnstr_t a, cnstr_t b) { return (a != 0) && (b != 0); }

cnstr_t _EQ_(symbolic a, symbolic b) { return a == b; }
cnstr_t _NEQ_(symbolic a, symbolic b) { return a != b; }

cnstr_t _LT_(symbolic a, symbolic b) { return a < b; }
cnstr_t _LE_(symbolic a, symbolic b) { return a <= b; }
cnstr_t _GT_(symbolic a, symbolic b) { return a > b; }
cnstr_t _GE_(symbolic a, symbolic b) { return a >= b; }

cnstr_t _ULT_(symbolic a, symbolic b)
{
    return (unsigned long)a < (unsigned long)b;
}

cnstr_t _ULE_(symbolic a, symbolic b)
{
    return (unsigned long)a <= (unsigned long)b;
}

cnstr_t _UGT_(symbolic a, symbolic b)
{
    return (unsigned long)a > (unsigned long)b;
}

cnstr_t _UGE_(symbolic a, symbolic b)
{
    return (unsigned long)a >= (unsigned long)b;
}

cnstr_t _ITE_(cnstr_t cond, cnstr_t a, cnstr_t b) { return cond ? a : b; }

symbolic _ITE_VAR_(cnstr_t cond, symbolic a, symbolic b)
{
    return cond ? a : b;
}

/* ------------------------------------------------------------------ */
/* Lists                                                               */
/* ------------------------------------------------------------------ */

static sbv_list *list_from_id(list_t id)
{
    if ((int)id >= g_nlists)
        fail("list handle out of range");
    return &g_lists[id];
}

static list_t list_new(void)
{
    list_t id;
    if (g_nlists >= SBV_MAX_LISTS)
        fail("too many lists");
    id = (list_t)g_nlists++;
    g_lists[id].len = 0;
    return id;
}

list_t lst_mk(void) { return list_new(); }

list_t lst_cons(symbolic value, list_t lst)
{
    /*
     * Destructive, matching the symbolic backend: _lst_prepend mutates the
     * deque in place and lst_cons returns the *same* handle.
     */
    sbv_list *l = list_from_id(lst);
    int i;

    if (l->len >= SBV_MAX_LIST_LEN)
        fail("list too long");

    for (i = l->len; i > 0; i--)
        l->items[i] = l->items[i - 1];

    l->items[0] = value;
    l->len++;
    return lst;
}

cnstr_t lst_empty(list_t lst) { return list_from_id(lst)->len == 0; }

list_t lst_tl(list_t lst)
{
    /* Non-destructive: returns a fresh handle holding the tail. */
    sbv_list *l = list_from_id(lst);
    list_t id;
    sbv_list *tail;
    int i;

    if (l->len == 0)
        fail("lst_tl on an empty list");

    id = list_new();
    tail = &g_lists[id];
    for (i = 1; i < l->len; i++)
        tail->items[i - 1] = l->items[i];
    tail->len = l->len - 1;
    return id;
}

symbolic lst_hd(list_t lst)
{
    sbv_list *l = list_from_id(lst);
    if (l->len == 0)
        fail("lst_hd on an empty list");
    return l->items[0];
}

size_t lst_len(list_t lst) { return (size_t)list_from_id(lst)->len; }

list_t lst_nbytes(char c, size_t n)
{
    list_t id = list_new();
    sbv_list *l = &g_lists[id];
    size_t i;

    if (n > SBV_MAX_LIST_LEN)
        fail("lst_nbytes: length too large");

    for (i = 0; i < n; i++)
        l->items[i] = (long)c;
    l->len = (int)n;
    return id;
}

list_t lst_zeros(size_t n) { return lst_nbytes(0, n); }

/* ------------------------------------------------------------------ */
/* Heap / memory                                                       */
/* ------------------------------------------------------------------ */

void is_rw(void *ptr, size_t size)
{
    /*
     * The symbolic backend walks angr's page permissions and raises on a
     * violation. Natively there is no cheap equivalent -- but a real
     * violation will be caught at the point of access by ASan/UBSan, with a
     * better report than we could produce here.
     */
    (void)ptr;
    (void)size;
}

void allocd(void *ptr, size_t size) { is_rw(ptr, size); }

int mallocd(void *ptr)
{
    int i;
    for (i = 0; i < g_nchunks; i++)
        if (g_chunks[i].ptr == ptr)
            return 1;
    return 0;
}

void cond_write(void *ptr, symbolic c, cnstr_t pc)
{
    if (pc)
        *(char *)ptr = (char)c;
}

void *mem_alloc(size_t bytes)
{
    /* 8-byte aligned, which is enough for every type the API traffics in. */
    size_t off = (g_arena_off + 7u) & ~(size_t)7u;
    void *ptr;

    if (off + bytes > SBV_ARENA_SIZE)
        fail("mem_alloc: arena exhausted");

    if (g_nchunks >= SBV_MAX_CHUNKS)
        fail("too many heap chunks");

    ptr = &g_arena[off];
    g_arena_off = off + bytes;

    g_chunks[g_nchunks].ptr = ptr;
    g_chunks[g_nchunks].size = bytes;
    g_nchunks++;
    return ptr;
}

void mem_free(void *ptr)
{
    int i;

    for (i = 0; i < g_nchunks; i++) {
        if (g_chunks[i].ptr == ptr) {
            /* Drop the bookkeeping only; the arena is rewound per exec. */
            g_chunks[i] = g_chunks[--g_nchunks];
            return;
        }
    }

    fail("mem_free: not a tracked chunk");
}

size_t n_allocd(void *ptr)
{
    int i;
    for (i = 0; i < g_nchunks; i++)
        if (g_chunks[i].ptr == ptr)
            return g_chunks[i].size;
    fail("n_allocd: not a tracked chunk");
    return 0;
}

/* ------------------------------------------------------------------ */
/* Validation API                                                      */
/* ------------------------------------------------------------------ */

void mem_addr(char *name, void *addr, size_t length)
{
    region_t *r;

    if (g_nregions >= SBV_MAX_REGIONS)
        fail("too many tagged memory regions");
    if (length > SBV_MAX_REGION_LEN)
        fail("tagged region too large");

    r = &g_regions[g_nregions++];
    sbv_strcpy(r->name, sizeof(r->name), name);
    r->addr = (unsigned char *)addr;
    r->len = length;

    /*
     * Snapshot at registration time. save_current_state() is emitted *before*
     * the mem_addr() calls, so it has nothing to record; this is the earliest
     * point at which the inputs are known, and it is what halt_all() restores.
     */
    sbv_memcpy(r->orig, r->addr, length);
}

state_t save_current_state(void) { return 1; }

void halt_all(state_t state)
{
    /* Roll the tagged inputs back so the summary sees what the concrete
     * function saw, undoing any out-parameter writes. */
    int i;
    (void)state;
    for (i = 0; i < g_nregions; i++)
        sbv_memcpy(g_regions[i].addr, g_regions[i].orig, g_regions[i].len);

    /* Rewind rather than reopen: it also clears the EOF and error flags, and
     * keeps the same FILE*, so the summary is handed the very pointer the
     * concrete function received. */
    for (i = 0; i < g_nstreams; i++)
        if (g_streams[i].fp != NULL)
            rewind(g_streams[i].fp);
}

cnstr_t get_cnstr(symbolic var, size_t size)
{
    /*
     * Capture the observable state: the return value plus the current
     * contents of every tagged region. The handle returned is an index into
     * the snapshot table; store_cnstr() is its only consumer, so it cannot be
     * confused with the 0/1 a constraint operator returns.
     */
    snapshot_t *s;
    cnstr_t handle;
    int i;

    if (g_nsnapshots >= SBV_MAX_SNAPSHOTS)
        fail("too many snapshots");

    handle = (cnstr_t)g_nsnapshots++;
    s = &g_snapshots[handle];
    s->used = 1;
    s->ret_len = 0;

    if (var != 0 && size != 0) {
        size_t nbytes = size / 8;
        if (nbytes > SBV_MAX_RET)
            nbytes = SBV_MAX_RET;
        sbv_memcpy(s->ret, (const void *)(size_t)var, nbytes);
        s->ret_len = nbytes;
    }

    s->nregions = g_nregions;
    for (i = 0; i < g_nregions; i++) {
        sbv_memcpy(s->mem[i], g_regions[i].addr, g_regions[i].len);
        s->mem_len[i] = g_regions[i].len;
    }

    return handle;
}

void store_cnstr(char *name, cnstr_t constraint)
{
    binding_t *b;

    if (g_nbindings >= SBV_MAX_NAMES)
        fail("too many stored constraints");

    b = &g_bindings[g_nbindings++];
    sbv_strcpy(b->name, sizeof(b->name), name);
    b->handle = constraint;
    b->used = 1;
}

static snapshot_t *lookup(const char *name)
{
    int i;
    for (i = 0; i < g_nbindings; i++)
        if (sbv_streq(g_bindings[i].name, name))
            return &g_snapshots[g_bindings[i].handle];
    return NULL;
}

static void hexdump(char *dst, size_t dstlen, const unsigned char *src,
                    size_t n)
{
    dst[0] = '\0';
    sbv_hex(dst, dstlen, 0, src, n);
}

/* Value of a snapshot's return bytes, as an integer. */
static size_t ret_value(const snapshot_t *s)
{
    size_t value = 0;
    size_t i;

    for (i = 0; i < s->ret_len && i < sizeof(size_t); i++)
        value |= ((size_t)s->ret[i]) << (8 * i);

    return value;
}

static const chunk_t *chunk_of(size_t addr)
{
    int i;

    for (i = 0; i < g_nchunks; i++)
        if ((size_t)g_chunks[i].ptr == addr)
            return &g_chunks[i];

    return NULL;
}

/*
 * Compare two returned heap pointers by what they point at.
 *
 * A function that returns freshly allocated memory (strdup) hands back a
 * different address on each call, so comparing the addresses themselves
 * always "diverges". The symbolic engine sidesteps this by treating the
 * address as existentially quantified; concretely the equivalent is to
 * compare the allocations' contents.
 *
 * Recognising a return value as a pointer is a heuristic -- it is whatever
 * matches a tracked allocation -- but an integer return that collides with a
 * live chunk address is not a realistic possibility.
 *
 * Returns 0 if equal, 1 if they differ, -1 if this is not a pointer pair.
 */
static int compare_allocations(const snapshot_t *cncrt, const snapshot_t *summ)
{
    const chunk_t *a = chunk_of(ret_value(cncrt));
    const chunk_t *b = chunk_of(ret_value(summ));

    if (!a || !b)
        return -1;

    if (a->size != b->size)
        return 1;

    return sbv_memcmp(a->ptr, b->ptr, a->size) != 0;
}

result_t check_implications(char *constraint1, char *constraint2)
{
    /*
     * Concrete counterpart of the implication check: with a single concrete
     * input both sides denote exactly one value, so the check degenerates to
     * equality of the observable state.
     */
    snapshot_t *cncrt = lookup(constraint1);
    snapshot_t *summ = lookup(constraint2);
    int i;

    g_ntests++;

    if (!cncrt || !summ)
        fail("check_implications: unknown constraint name");

    if (cncrt->ret_len != summ->ret_len ||
        sbv_memcmp(cncrt->ret, summ->ret, cncrt->ret_len) != 0) {

        int alloc = compare_allocations(cncrt, summ);

        if (alloc == 1) {
            const chunk_t *a = chunk_of(ret_value(cncrt));
            const chunk_t *b = chunk_of(ret_value(summ));
            char x[128], y[128];

            hexdump(x, sizeof(x), (const unsigned char *)a->ptr, a->size);
            hexdump(y, sizeof(y), (const unsigned char *)b->ptr, b->size);
            snprintf(g_report, sizeof(g_report),
                     "returned allocation (%lu vs %lu bytes): concrete=%s "
                     "summary=%s", (unsigned long)a->size,
                     (unsigned long)b->size, x, y);
            g_diverged_test = g_ntests;
            return 1;
        }

        if (alloc < 0) {
            char a[64], b[64];

            /* Returns are compared bit for bit, on purpose: -0.0 and +0.0 are
             * `==` but tell apart under signbit() and 1/x, so a summary that
             * confuses them is not observationally equivalent. That is easy to
             * defend and impossible to read off two hex blobs, so a
             * float-width return is rendered as a float as well. */
            if (returns_float(cncrt, summ)) {
                render_float(a, sizeof(a), cncrt->ret, cncrt->ret_len);
                render_float(b, sizeof(b), summ->ret, summ->ret_len);
                snprintf(g_report, sizeof(g_report),
                         "return value: concrete=%s summary=%s", a, b);
                g_diverged_test = g_ntests;
                return 1;
            }

            hexdump(a, sizeof(a), cncrt->ret, cncrt->ret_len);
            hexdump(b, sizeof(b), summ->ret, summ->ret_len);
            snprintf(g_report, sizeof(g_report),
                     "return value: concrete=0x%s summary=0x%s", a, b);
            g_diverged_test = g_ntests;
            return 1;
        }

        /* alloc == 0: different addresses, identical contents. */
    }

    for (i = 0; i < cncrt->nregions && i < summ->nregions; i++) {
        if (cncrt->mem_len[i] != summ->mem_len[i] ||
            sbv_memcmp(cncrt->mem[i], summ->mem[i], cncrt->mem_len[i]) != 0) {
            char a[128], b[128], o[128];
            hexdump(a, sizeof(a), cncrt->mem[i], cncrt->mem_len[i]);
            hexdump(b, sizeof(b), summ->mem[i], summ->mem_len[i]);
            /* The pre-state makes the diff readable: without it you cannot
             * tell which side wrote what. */
            hexdump(o, sizeof(o), g_regions[i].orig, g_regions[i].len);
            snprintf(g_report, sizeof(g_report),
                     "memory '%s': before=%s concrete=%s summary=%s",
                     g_regions[i].name, o, a, b);
            g_diverged_test = g_ntests;
            return 1;
        }
    }

    return 0;
}

void print_counterexamples(result_t result)
{
    /* The driver owns reporting; it has the input tape that produced this. */
    (void)result;
}

/* ------------------------------------------------------------------ */
/* Driver interface                                                    */
/* ------------------------------------------------------------------ */

static void reset(const unsigned char *data, size_t len)
{
    g_input = data;
    g_input_len = len;
    g_input_pos = 0;

    for (int i = 0; i < g_nstreams; i++) {
        if (g_streams[i].fp != NULL) {
            fclose(g_streams[i].fp);
            g_streams[i].fp = NULL;
        }
    }
    g_nstreams = 0;

    g_nregions = 0;
    g_nsnapshots = 0;
    g_nbindings = 0;
    g_nlists = 0;

    g_rejected = 0;
    g_diverged_test = 0;
    g_ntests = 0;
    g_ndraws = 0;
    g_report[0] = '\0';
    g_inputs[0] = '\0';

    g_nchunks = 0;
    g_arena_off = 0;
}

int sbv_fuzz_exec(const unsigned char *data, size_t len, int (*entry)(void))
{
    reset(data, len);
    g_total_execs++;

    if (setjmp(g_reject_jmp) != 0) {
        g_total_rejected++;
        return SBV_REJECTED;
    }

    entry();

    if (g_diverged_test)
        return SBV_DIVERGED;
    return SBV_OK;
}

const char *sbv_fuzz_inputs(void)
{
    size_t off = 0;
    int i;

    g_inputs[0] = '\0';

    for (i = 0; i < g_ndraws && off + 32 < sizeof(g_inputs); i++) {
        draw_t *d = &g_draws[i];

        if (d->raw) {
            /* Today only floating-point arguments take the sym_var_bytes()
             * path, so a raw draw of float width is one. Should the primitive
             * ever be reused (long long, opaque handles), this needs a type
             * tag rather than a width guess -- printing a `long long` as a
             * double would be worse than useless in a counterexample. */
            if (d->bits == 32) {
                float f;
                memcpy(&f, d->bytes, sizeof(f));
                off += (size_t)snprintf(g_inputs + off, sizeof(g_inputs) - off,
                                        "%s%s=%g", off ? " " : "", d->name,
                                        (double)f);
            } else if (d->bits == 64) {
                double v;
                memcpy(&v, d->bytes, sizeof(v));
                off += (size_t)snprintf(g_inputs + off, sizeof(g_inputs) - off,
                                        "%s%s=%g", off ? " " : "", d->name, v);
            } else {
                off += (size_t)snprintf(g_inputs + off, sizeof(g_inputs) - off,
                                        "%s%s=<%lu bits>", off ? " " : "",
                                        d->name, (unsigned long)d->bits);
            }
        } else if (d->indexed)
            off += (size_t)snprintf(g_inputs + off, sizeof(g_inputs) - off,
                                    "%s%s[%ld]=0x%02lx", off ? " " : "",
                                    d->name, d->index,
                                    (unsigned long)(d->value & 0xff));
        else
            off += (size_t)snprintf(g_inputs + off, sizeof(g_inputs) - off,
                                    "%s%s=%ld", off ? " " : "",
                                    d->name, d->value);
    }

    return g_inputs;
}

unsigned long sbv_fuzz_total_execs(void) { return g_total_execs; }
unsigned long sbv_fuzz_total_rejected(void) { return g_total_rejected; }

size_t sbv_fuzz_consumed(void)
{
    return g_input_pos < g_input_len ? g_input_pos : g_input_len;
}

int sbv_fuzz_diverged_test(void) { return g_diverged_test; }

int sbv_fuzz_ntests(void) { return g_ntests; }

const char *sbv_fuzz_report(void) { return g_report; }
