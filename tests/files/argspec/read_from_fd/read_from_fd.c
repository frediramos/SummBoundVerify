typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define READ_SIZE 4

ssize_t read_from_fd(int fd, char *buf)
{
  ssize_t nread = __file_read(fd, buf, READ_SIZE);
  if (__is_certain(_LT_(nread, 0)))
  {
    return -1;
  }
  __assume(_GE_(nread, 0));
  return nread;
}
