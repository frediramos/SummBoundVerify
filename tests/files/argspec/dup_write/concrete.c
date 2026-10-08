int concrete_dup_write(int fd, const char *data)
{
  int fd2 = dup(fd);
  if (fd2 < 0)
    return -1;
  if (write(fd2, data, 4) != 4)
  {
    close(fd2);
    return -1;
  }
  close(fd2);
  return fd2;
}
