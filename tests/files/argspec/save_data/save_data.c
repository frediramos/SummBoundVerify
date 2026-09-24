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
  if (__is_certain(_NEQ_(ret, 1)))
  {
    return -1;
  }
  __assume(_EQ_(ret, 1));
  int fd = __file_open(path, "w");
  if (__is_certain(_LT_(fd, 0)))
  {
    return -1;
  }
  __assume(_GE_(fd, 0));
  fork_save_data(len);
  int written = __file_write(fd, data, len);
  __file_close(fd);
  if (__is_certain(_NEQ_(written, len)))
  {
    return -1;
  }
  __assume(_EQ_(written, len));
  return 0;
}
