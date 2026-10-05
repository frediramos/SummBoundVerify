#include "sra.h"
#include "utils.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int fd = __file_open("abc", "r+");

  __sra_assert(ret1 == 1);
  __sra_assert(fd == 3);

  ssize_t offset1 = __file_offset(fd);
  __sra_assert(offset1 == 0);

  ssize_t set = __file_set_offset(fd, 5);
  __sra_assert(set == 5);

  ssize_t offset2 = __file_offset(fd);
  __sra_assert(offset2 == 5);

}