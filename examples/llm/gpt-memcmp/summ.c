// https://chatgpt.com/share/69adbffc-b164-8011-8772-c25b03ea470c

int summ_memcmp(const void* lhs, const void* rhs, size_t count) {
    unsigned char *l = (unsigned char*) lhs;
    unsigned char *r = (unsigned char*) rhs;

    if(is_symbolic(count)){
        count = maximize(count);
    }

    int result = 0;
    for(size_t i = 0; i < count; i++){
        unsigned char lc = l[i];
        unsigned char rc = r[i];

        // compute first differing byte
        if(!is_symbolic(result)){
            if(is_symbolic(lc) || is_symbolic(rc) || lc != rc){
                result = (int)lc - (int)rc;
            }
        }
    }
    return result;
}