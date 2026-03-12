// https://claude.ai/share/85623d45-d6ad-4590-b03f-16b06ea5eb53

char *strncpy1(char *dest, const char *src, size_t n) {

    // If n is symbolic, maximize and constrain to concrete value
    if (is_symbolic(n)) {
        size_t max = maximize(n);
        cnstr_t c_max = _EQ_(n, max);
        assume(c_max);
        n = max;
    }

    char *str_dest = dest;
    const char *str_src = src;

    size_t i = 0;

    // Copy src characters up to n, stopping at null terminator
    for (i = 0; i < n; i++) {
        char c;

        if (is_symbolic(*(str_src + i))) {
            c = *(str_src + i);
        } else {
            c = *(str_src + i);
        }

        *(str_dest + i) = c;

        // If we hit null terminator in src, pad remainder with nulls
        if (c == '\0') {
            i++;
            break;
        }
    }

    // Pad remaining bytes with null characters
    for (; i < n; i++) {
        *(str_dest + i) = '\0';
    }

    return dest;
}