#include "sra.h"

int main(){

  int ret = __file_create("abc");
  __sra_assert(ret == 1);

  int fd = __file_open("abc", "r+");
  __sra_assert(fd == 3);

  // Duplicating an fd onto itself does nothing
  int fd2 = __file_dup2(fd, fd);
  __sra_assert(fd2 == fd);

  int count = __file_write(fd, "123", 3);
  __sra_assert(count == 3);
  __sra_assert(__file_offset(fd) == 3);
}
