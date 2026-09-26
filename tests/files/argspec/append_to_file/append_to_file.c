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
  /* O_APPEND: every write goes to the end of the file. */
  __file_set_offset(fd, __file_size(fd));
  __file_write(fd, "cd", 2);
  return fd;
}
