#include "sra.h"

int main(){

  int ret = __file_create("abc");
  __assert(ret == 1);

  int fd = __file_open("abc", "r+");
  __assert(fd == 3);
  __assert(__file_close(fd) == 0);

  char buffer[3];
  mode_t mode;

  // A closed fd behaves like one that was never opened
  int fds[2] = {fd, 42};

  for (int i = 0; i < 2; i++){
    int f = fds[i];
    __assert(__file_close(f) == -1);
    __assert(__file_write(f, "12", 2) == -1);
    __assert(__file_read(f, buffer, 2) == -1);
    __assert(__file_size(f) == -1);
    __assert(__file_offset(f) == -1);
    __assert(__file_set_size(f, 2) == -1);
    __assert(__file_set_offset(f, 2) == -1);
    __assert(__file_set_mode(f, 0644) == -1);
    __assert(__file_mode(f, &mode) == -1);
    __assert(__file_flags(f) == -1);
    __assert(__file_dup(f) == -1);
    __assert(__file_dup2(f, 5) == -1);
    __assert(__FILE_from_fd(f) == NULL);
  }
}
