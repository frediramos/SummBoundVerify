#include "sra.h"

int main(){

  __file_create("abc");
  int fd = __file_open("abc", "r+");
  __sra_assert(__file_set_mode(fd, 0444) == 1);
  __file_close(fd);

  // The mode belongs to the file: it outlives the descriptor
  fd = __file_open("abc", "r");
  mode_t mode;
  __sra_assert(__file_mode(fd, &mode) == 1);
  __sra_assert(mode == 0444);
}
