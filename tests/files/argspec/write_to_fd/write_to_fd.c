typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 5

ssize_t write_to_fd(int fd, const char *data)
{
  ssize_t written = __file_write(fd, data, WRITE_SIZE);
  if (__is_certain(_LT_(written, 0)))
  {
    return -1;
  }
  return written;
}
