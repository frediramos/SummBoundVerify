#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int fd = __file_open("abc", "r+");

  __sra_assert(ret1 == 1);
  __sra_assert(fd == 3);

  ssize_t size1 = __file_size(fd);
  __sra_assert(size1 == 0);

  ssize_t set = __file_set_size(fd, 5);
  __sra_assert(set == 5);

  ssize_t size2 = __file_size(fd);
  __sra_assert(size2 == 5);

}