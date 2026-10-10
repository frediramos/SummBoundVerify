#include "sra.h"

int main(){

  __file_create("abc");

  // Descriptors 0 to 4: 0, 1 and 2 are taken, so 3 and 4 are left
  __sra_assert(__file_set_max_fds(5) == 1);

  int fd1 = __file_open("abc", "r");
  int fd2 = __file_open("abc", "r");
  __sra_assert(fd1 == 3);
  __sra_assert(fd2 == 4);

  // The table is full: open and dup fail (EMFILE)
  __sra_assert(__file_open("abc", "r") == -1);
  __sra_assert(__file_dup(fd1) == -1);
}
