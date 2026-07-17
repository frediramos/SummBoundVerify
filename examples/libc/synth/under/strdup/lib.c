typedef unsigned int size_t;

char *strcpy(char *dest, const char *src) {
  size_t i;
  for(i = 0;; i++){
    char d = src[i];
    dest[i] = d;
    if(d == 0) return dest;
  }
}

size_t strlen(const char *str) {
  size_t i;
  for (i=0; ; i++)
    if (str[i]==0) return i;
}

void* malloc(size_t size){
    return mem_alloc(size);
}