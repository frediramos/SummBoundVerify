typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

int reopen_file(const char *path)
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
  __file_write(fd, "abc", 3);
  __file_close(fd);
  return __file_open(path, "w");
}
