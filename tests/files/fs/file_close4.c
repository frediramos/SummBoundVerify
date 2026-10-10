#include "sra.h"

int main(){

  __file_create("abc");

  // Two opens of the same file, closed in the order they were opened
  int fd1 = __file_open("abc", "r");
  int fd2 = __file_open("abc", "r");
  int fd3 = __file_dup(fd2);

  __sra_assert(__file_close(fd1) == 0);
  __sra_assert(__file_close(fd2) == 0);
  __sra_assert(__file_close(fd3) == 0);
}
