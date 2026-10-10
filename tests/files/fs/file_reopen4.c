#include "sra.h"

int main(){

  __file_create("abc");
  int fd = __file_open("abc", "r+");
  __file_write(fd, "12345", 5);
  __file_close(fd);

  // A deleted file comes back empty when created again
  __sra_assert(__file_delete("abc") == 1);
  __sra_assert(__file_create("abc") == 1);

  fd = __file_open("abc", "r");
  __sra_assert(__file_size(fd) == 0);
}
