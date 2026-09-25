typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
typedef struct _IO_FILE FILE;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 4

size_t fwrite_to_fp(FILE *fp, const char *data)
{
  int fd = __fd_from_FILE(fp);
  if (__is_certain(_LT_(fd, 0)))
  {
    return 0;
  }
  __assume(_GE_(fd, 0));
  ssize_t written = __file_write(fd, data, WRITE_SIZE);
  __file_close(fd);
  if (__is_certain(_LT_(written, 0)))
  {
    return 0;
  }
  __assume(_GE_(written, 0));
  return written;
}
