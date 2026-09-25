#include "sra.h"

#define SIZE 3

int main(){
  
  char s1[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';

  // File names cannot be empty
  __assume(_NEQ_(s1[0], 0));

  int ret1 = __file_create(s1);
  int fd = __file_open(s1, "r+");
  __assert(ret1 == 1);
  __assert(fd == 3);

  ssize_t offset1 = __file_offset(fd);
  __assert(offset1 == 0);

  ssize_t set = __file_set_offset(fd, 5);
  __assert(set == 5);

  ssize_t offset2 = __file_offset(fd);
  __assert(offset2 == 5);

}