size_t concrete_strlen(const char *str) {
  size_t i;
  for (i=0; ; i++)
    if (str[i]==0) return i;
}