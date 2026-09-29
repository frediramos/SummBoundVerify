int concrete_create_file(const char *path)
{
  FILE *f = fopen(path, "w");
  if (!f)
    return -1;
  fclose(f);
  return 1;
}
