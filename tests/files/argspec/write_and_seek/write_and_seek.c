typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 4

ssize_t write_and_seek(int fd, const char *data)
{
  ssize_t written = __file_write(fd, data, WRITE_SIZE);
  if (__is_certain(_LT_(written, 0)))
  {
    return -1;
  }
  __assume(_GE_(written, 0));
  int pos = __file_set_offset(fd, 0);
  if (__is_certain(_LT_(pos, 0)))
  {
    return -1;
  }
  __assume(_GE_(pos, 0));
  return written;
}
