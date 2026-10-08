typedef unsigned int size_t;
typedef int ssize_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

#define WRITE_SIZE 5

ssize_t write_to_fd(int fd, const char *data)
{
  ssize_t written = __file_write(fd, data, WRITE_SIZE);
  /* Bug on purpose: the summary opens a second file the concrete function
   * never does. Its descriptor is open only on the summary's side, so the
   * fuzz engine must report the open-descriptor sets as a mismatch. */
  __file_create("zz");
  int fd2 = __file_open("zz", "w");
  __file_write(fd2, "junk", 4);
  if (__is_certain(_LT_(written, 0)))
  {
    return -1;
  }
  return written;
}
