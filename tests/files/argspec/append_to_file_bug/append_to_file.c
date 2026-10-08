typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

int append_to_file(const char *path)
{
  int ret = __file_create(path);
  if (ret != 1)
  {
    return -1;
  }
  int fd = __file_open(path, "a");
  if (fd < 0)
  {
    return -1;
  }
  __file_write(fd, "ab", 2);
  __file_set_offset(fd, 0);
  /* Bug on purpose: O_APPEND is ignored, so "cd" overwrites "ab" instead of
   * following it. The fuzz engine must report the concrete "abcd" as a
   * mismatch. */
  __file_write(fd, "cd", 2);
  return fd;
}
