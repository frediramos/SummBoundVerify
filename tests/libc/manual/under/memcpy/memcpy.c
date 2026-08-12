void* summ_memcpy(void *dest, void *src, size_t n){

	//If length is symbolic maximize and constrain to a concrete length
	if(__is_symbolic(n)){

		size_t max = __maximize(n);
		cnstr_t __maximize = _EQ_(n, max);
		__assume(__maximize);
		n = max;
	}
	
	unsigned char *str_dest = (unsigned char*) dest;
	unsigned char *str_src = (unsigned char*) src;

	for(int i = 0; i < n; i++){

		unsigned char c = *(str_src + i);
		*(str_dest + i) = c;

	}
	return dest;
}