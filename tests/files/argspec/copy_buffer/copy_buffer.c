void copy_buffer(char *dst, const char *src)
{
  for (int i = 0; i < 4; i++)
    dst[i] = src[i];
}
