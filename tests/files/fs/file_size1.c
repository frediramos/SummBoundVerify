#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int fd = __file_open("abc", "r+");

  __sra_assert(ret1 == 1);
  __sra_assert(fd == 3);

  ssize_t size = __file_size(fd);
  __sra_assert(size == 0);

}