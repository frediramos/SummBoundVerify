size_t concrete_fwrite_to_fp(FILE *fp, const char *data)
{
  return fwrite(data, 1, 4, fp);
}
