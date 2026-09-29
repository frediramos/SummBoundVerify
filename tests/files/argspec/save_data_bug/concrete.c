int concrete_save_data(const char *path, const char *data, size_t len)
{
  int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd < 0)
    return -1;

  size_t total = 0;
  while (total < len)
  {
    ssize_t n = write(fd, data + total, len - total);
    if (n <= 0)
    {
      close(fd);
      return -1;
    }
    total += n;
  }

  return 0;
}
