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

  // No valid_fname: the name may be empty, but it is certainly the name
  // the file was created under, so the open shares the file
  __file_create(s1);
  int fd = __file_open(s1, "r+");
  __file_write(fd, "12345", 5);
  __file_set_mode(fd, 0600);
  __file_close(fd);

  __assume(_NEQ_(s1[0], 0));

  // The contents and the mode outlive the descriptor
  fd = __file_open(s1, "r");
  __sra_assert(__file_size(fd) == 5);

  mode_t mode;
  __file_mode(fd, &mode);
  __sra_assert(mode == 0600);
}
