ssize_t concrete_read_from_fd(int fd, char *buf)
{
  ssize_t nread = read(fd, buf, 4);
  if (nread < 0)
    return -1;
  return nread;
}
