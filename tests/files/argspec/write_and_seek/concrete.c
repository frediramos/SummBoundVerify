ssize_t concrete_write_and_seek(int fd, const char *data)
{
  ssize_t written = write(fd, data, 4);
  if (written < 0)
    return -1;
  off_t pos = lseek(fd, 0, 0);
  if (pos < 0)
    return -1;
  return written;
}
