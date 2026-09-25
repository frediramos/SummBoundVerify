#include "sra.h"

#define SIZE 4

int main(){
  
  char s1[SIZE];
  char s2[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }
  
  // Concrete null byte
  s1[SIZE-1] = '\0';

  // File names cannot be empty
  __assume(_NEQ_(s1[0], 0));

  int ret1 = __file_create(s1);
  __assert(ret1 == 1);
  
  int ret2 = __file_open("abc", "r+");
  __assert(ret2 == 3);

}