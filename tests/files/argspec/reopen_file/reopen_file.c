typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

int reopen_file(const char *path)
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
  __file_write(fd, "abc", 3);
  __file_close(fd);
  return __file_open(path, "w");
}
