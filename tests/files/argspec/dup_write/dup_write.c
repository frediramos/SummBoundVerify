typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 4

int dup_write(int fd, const char *data)
{
  int fd2 = __file_dup(fd);
  if (fd2 < 0)
  {
    return -1;
  }
  ssize_t written = __file_write(fd2, data, WRITE_SIZE);
  if (written != WRITE_SIZE)
  {
    __file_close(fd2);
    return -1;
  }
  __file_close(fd2);
  return fd2;
}
