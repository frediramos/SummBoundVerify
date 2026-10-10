#include "sra.h"

int main(){

  __file_create("abc");
  __file_set_max_fds(5);

  int fd = __file_open("abc", "r");

  // dup2 onto a descriptor past the limit fails (EBADF)
  __sra_assert(__file_dup2(fd, 5) == -1);
  __sra_assert(__file_dup2(fd, 4) == 4);
}
