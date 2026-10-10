#include "sra.h"

int main(){

  // As the testsuite's create_test_file: set the size, then close
  __file_create("abc");
  int fd = __file_open("abc", "r+");
  __sra_assert(__file_set_size(fd, 10) == 10);
  __file_close(fd);

  fd = __file_open("abc", "r");
  __sra_assert(__file_size(fd) == 10);
}
