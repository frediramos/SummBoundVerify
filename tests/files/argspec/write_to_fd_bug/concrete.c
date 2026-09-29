ssize_t concrete_write_to_fd(int fd, const char *data)
{
  ssize_t written = write(fd, data, 5);
  if (written < 0)
    return -1;
  return written;
}
