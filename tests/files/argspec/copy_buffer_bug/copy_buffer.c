void copy_buffer(char *dst, const char *src)
{
  for (int i = 0; i < 4; i++)
    dst[i] = src[i];

  /* Bug on purpose: the summary wipes the source, which the function only
   * reads. `src` is `type: read` in the argspec, so this is caught only
   * because read regions are tagged and compared too. */
  for (int i = 0; i < 4; i++)
    ((char *)src)[i] = 0;
}
