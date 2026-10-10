#include "sra.h"

int main(){

  __file_create("abc");
  __file_set_max_fds(5);

  int fd1 = __file_open("abc", "r");
  int fd2 = __file_open("abc", "r");

  // Closing a descriptor frees its slot
  __file_close(fd1);
  __sra_assert(__file_open("abc", "r") == 3);
}
