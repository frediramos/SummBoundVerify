#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int fd = __file_open("abc", "r+");

  __assert(ret1 == 1);
  __assert(fd == 3);

  ssize_t offset = __file_offset(fd);
  __assert(offset == 0);

}