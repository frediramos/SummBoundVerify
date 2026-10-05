#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  __sra_assert(ret1 == 1);
  
  int fd = __file_open("abc", "r");
  __sra_assert(fd == 3);

  FILE* fp = __FILE_from_fd(fd);
  int fd2 = __fd_from_FILE(fp);
  
  __sra_assert(fd == fd2);
}