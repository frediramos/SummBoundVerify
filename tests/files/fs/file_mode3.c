#include "sra.h"

int main(){

  __file_create("abc");
  int fd1 = __file_open("abc", "r+");
  int fd2 = __file_open("abc", "r");
  int fd3 = __file_dup(fd1);

  // A mode set through one descriptor is seen through the others
  __file_set_mode(fd1, 0600);

  mode_t mode;
  __file_mode(fd2, &mode);
  __sra_assert(mode == 0600);
  __file_mode(fd3, &mode);
  __sra_assert(mode == 0600);
}
