#include "sra.h"

#define SIZE 3

int main(){

  char s1[SIZE];

  // Fill with symbolic bytes, possibly an empty (invalid) name
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';

  __file_create(s1);

  // fd = ite(valid, 3, -1)
  int fd = __file_open(s1, "r");
  __assert((fd == 3) | (fd == -1));

  // fp = ite(valid, fp, NULL)
  FILE* fp = __FILE_from_fd(fd);
  __assert((fd == -1) == (fp == NULL));

  int fd2 = __fd_from_FILE(fp);
  __assert(fd == fd2);
}
