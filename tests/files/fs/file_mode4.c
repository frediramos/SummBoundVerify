#include "sra.h"

int main(){

  __file_create("abc");
  int fd = __file_open("abc", "r+");
  __file_set_mode(fd, 0000);
  __file_close(fd);

  // A file created again gets the default mode
  __file_delete("abc");
  __file_create("abc");

  fd = __file_open("abc", "r");
  mode_t mode;
  __file_mode(fd, &mode);
  __sra_assert(mode == 0644);
}
