#include "sra.h"

#define SIZE 3

int main(){
  
  int ret = __file_create("abc");
  int fd = __file_open("abc", "r+");
  __sra_assert(ret == 1);
  __sra_assert(fd == 3);

  mode_t mode;

  __file_mode(fd, &mode);
  __sra_assert(mode == 0644);

  __file_set_mode(fd, 0777);
  __file_mode(fd, &mode);

  __sra_assert(mode == 0755);
}