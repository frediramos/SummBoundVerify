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

  __sra_assert(__file_create(s1) == 1);

  int fd = __file_open(s1, "r+");
  __sra_assert(__file_write(fd, "12345", 5) == 5);
  __sra_assert(__file_close(fd) == 0);

  // The contents outlive the descriptor, for a symbolic name too
  fd = __file_open(s1, "r");
  __sra_assert(fd == 3);
  __sra_assert(__file_size(fd) == 5);
}
