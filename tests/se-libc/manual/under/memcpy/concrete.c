void* concrete_memcpy(void *dest, void *src, size_t n){

	unsigned char *str_dest = (unsigned char*) dest;
	unsigned char *str_src = (unsigned char*) src;
	
	for(int i = 0; i < n; i++){//Path explosion

		unsigned char c = *(str_src + i);
		*(str_dest + i) = c;
	}
	return dest;
}
