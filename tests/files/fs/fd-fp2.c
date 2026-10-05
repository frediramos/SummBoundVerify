#include "sra.h"
#include "utils.h"

#define SIZE 3

int main(){

  char s1[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }
  
  // Concrete null byte
  s1[SIZE-1] = '\0';

  valid_fname(s1);
  
  int ret1 = __file_create(s1);
  __sra_assert(ret1 == 1);
  
  int fd = __file_open(s1, "r");
  __sra_assert(fd == 3);

  FILE* fp = __FILE_from_fd(fd);
  int fd2 = __fd_from_FILE(fp);
  
  __sra_assert(fd == fd2);
}