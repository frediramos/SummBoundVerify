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

  int ret1 = __file_create(s1);
  __assert(ret1 == 1);
  
  int fd = __file_open(s1, "r+");
  __assert(fd == 3);

  int count1 = __file_write(fd, "abc", 3);
  int count2 = __file_write(fd, "def", 3);

  __assert(count1 == 3);
  __assert(count2 == 3);

}