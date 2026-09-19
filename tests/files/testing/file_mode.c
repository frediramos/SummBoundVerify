#include "sra.h"

#define SIZE 3

int main(){
  
  int ret = __file_create("abc");
  int fd = __file_open("abc", "r+");
  __assert(ret == 1);
  __assert(fd == 3);

  mode_t mode;

  __file_mode(fd, &mode);
  __assert(mode == 0644);

  __file_set_mode(fd, 0777);
  __file_mode(fd, &mode);

  __assert(mode == 0755);
}