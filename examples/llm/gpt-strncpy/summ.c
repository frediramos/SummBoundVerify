// https://chatgpt.com/share/69b42c42-7638-8011-8f35-b7f48ab2e463

char *strncpy(char *dest, const char *src, size_t n) {

    /* Concretize symbolic length to avoid path explosion */
    if (is_symbolic(n)) {
        size_t max = maximize(n);
        assume(_EQ_(n, max));
        n = max;
    }

    char *d = dest;
    const char *s = src;

    int stop = 0;

    for (size_t i = 0; i < n; i++) {

        char c = *(s + i);

        /* detect first null byte in src */
        if (!stop) {
            push_pc();
            if (is_sat(_EQ_(c, 0))) {
                assume(_EQ_(c, 0));
                stop = 1;
            }
            pop_pc();
        }

        if (!stop) {
            *(d + i) = c;
        } else {
            *(d + i) = 0;
        }
    }

    return dest;
}