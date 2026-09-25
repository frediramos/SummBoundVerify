size_t concrete_fwrite_to_fp(FILE *fp, const char *data)
{
  size_t n = fwrite(data, 1, 4, fp);
  fclose(fp);
  return n;
}
