int concrete_create_and_delete(const char *path)
{
  int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0644);
  if (fd < 0)
    return -1;
  close(fd);
  if (unlink(path) != 0)
    return -1;
  return 1;
}
