#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int fd = __file_open("abc", "r+");

  __sra_assert(ret1 == 1);
  __sra_assert(fd == 3);

  ssize_t offset = __file_offset(fd);
  __sra_assert(offset == 0);

}