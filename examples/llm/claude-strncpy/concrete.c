char* concrete_strncpy(char* dest, char* src, size_t n){
  size_t i;

  for (i = 0; src[i] != '\0' && i < n; i++)
      dest[i] = src[i];
  for ( ; i < n; i++) //Symbolic n causes path explosion
      dest[i] = '\0';

  return dest;
}