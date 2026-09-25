int concrete_reopen_file(const char *path)
{
  int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd < 0)
    return -1;
  write(fd, "abc", 3);
  close(fd);
  /* Reuses the descriptor number just released. */
  return open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
}
