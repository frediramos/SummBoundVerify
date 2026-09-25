int concrete_append_to_file(const char *path)
{
  int fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0644);
  if (fd < 0)
    return -1;
  write(fd, "ab", 2);
  /* O_APPEND ignores the seek: the next write still lands at the end. */
  lseek(fd, 0, SEEK_SET);
  write(fd, "cd", 2);
  return fd;
}
