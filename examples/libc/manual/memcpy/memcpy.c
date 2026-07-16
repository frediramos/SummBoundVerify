void* summ_memcpy(void *dest, void *src, size_t n){

	//If length is symbolic maximize and cnstrict to a concrete length
	if(is_symbolic(n)){

		size_t max = maximize(n);
		cnstr_t maximize = _EQ_(n, max);
		assume(maximize);
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