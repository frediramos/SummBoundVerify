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

  __file_create(s1);
  int fd = __file_open(s1, "r+");
  __file_set_mode(fd, 0222);
  __file_close(fd);

  // The mode outlives the descriptor, for a symbolic name too
  fd = __file_open(s1, "r");
  mode_t mode;
  __file_mode(fd, &mode);
  __sra_assert(mode == 0222);
}
