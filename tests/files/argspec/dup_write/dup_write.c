typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 4

int dup_write(int fd, const char *data)
{
  int fd2 = __file_dup(fd);
  if (__is_certain(_LT_(fd2, 0)))
  {
    return -1;
  }
  __assume(_GE_(fd2, 0));
  ssize_t written = __file_write(fd2, data, WRITE_SIZE);
  if (__is_certain(_NEQ_(written, WRITE_SIZE)))
  {
    __file_close(fd2);
    return -1;
  }
  __assume(_EQ_(written, WRITE_SIZE));
  __file_close(fd2);
  return fd2;
}
