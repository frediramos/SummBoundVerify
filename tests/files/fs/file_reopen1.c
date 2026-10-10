#include "sra.h"

int main(){

  int ret = __file_create("abc");
  __sra_assert(ret == 1);

  int fd = __file_open("abc", "r+");
  __sra_assert(__file_write(fd, "12345", 5) == 5);
  __sra_assert(__file_close(fd) == 0);

  // The contents outlive the descriptor
  fd = __file_open("abc", "r");
  __sra_assert(fd == 3);
  __sra_assert(__file_size(fd) == 5);

  char buffer[5];
  __sra_assert(__file_read(fd, buffer, 5) == 5);
  __sra_assert(buffer[0] == '1');
  __sra_assert(buffer[4] == '5');
}
