#include "sra.h"

int main(){

  __file_create("abc");
  int fd = __file_open("abc", "r+");
  __file_write(fd, "12345", 5);
  __file_close(fd);

  // Another file is created after "abc", and both are reopened
  __file_create("def");
  int fd2 = __file_open("def", "r+");
  __file_write(fd2, "12", 2);
  __file_close(fd2);

  fd = __file_open("abc", "r");
  __sra_assert(__file_size(fd) == 5);

  fd2 = __file_open("def", "r");
  __sra_assert(__file_size(fd2) == 2);
}
