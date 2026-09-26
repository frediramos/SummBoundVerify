typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

void fork_save_data(unsigned int n)
{
  if (n == 0)
    return;
  fork_save_data(n - 1);
}

int save_data(const char *path, const char *data, size_t len)
{
  int ret = __file_create(path);
  if (ret != 1)
  {
    return -1;
  }
  int fd = __file_open(path, "w");
  if (fd < 0)
  {
    return -1;
  }
  fork_save_data(len);
  int written = __file_write(fd, data, len);
  /* Bug on purpose: the summary closes the file, but the concrete function
   * leaves it open. The descriptor is open only on the concrete side, so the
   * fuzz engine must report the open-descriptor sets as a mismatch. */
  __file_close(fd);
  if (written != len)
  {
    return -1;
  }
  return 0;
}
