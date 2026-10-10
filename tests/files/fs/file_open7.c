#include "sra.h"

int main(){

  __file_create("abc");

  // "abc" is no longer the latest file created
  __file_create("def");

  int fd1 = __file_open("abc", "r+");
  __sra_assert(__file_write(fd1, "12345", 5) == 5);

  // A second open of the same file has its own offset
  int fd2 = __file_open("abc", "r+");
  __sra_assert(__file_offset(fd2) == 0);
  __sra_assert(__file_offset(fd1) == 5);

  __sra_assert(__file_write(fd2, "xy", 2) == 2);
  __sra_assert(__file_offset(fd2) == 2);
  __sra_assert(__file_offset(fd1) == 5);

  // But the same file: fd1 sees what fd2 wrote
  __sra_assert(__file_set_offset(fd1, 0) == 0);

  char buffer[2];
  __sra_assert(__file_read(fd1, buffer, 2) == 2);
  __sra_assert(buffer[0] == 'x');
  __sra_assert(buffer[1] == 'y');
}
