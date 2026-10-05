#include "sra.h"
#include "utils.h"

#define SIZE 3

int main(){
  
  char s1[SIZE];
  char s2[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }
  
  for (int i = 0; i < SIZE; i++){
    s2[i] = __sym_var_array("s2", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';
  s2[SIZE-1] = '\0';

  valid_fname(s1);
  valid_fname(s2);

  int ret1 = __file_create(s1);
  __sra_assert(ret1 == 1);

  int ret2 = __file_open(s1, "r");
  __sra_assert(ret2 == 3);

  int ret3 = __file_delete(s2);
  __sra_assert(ret3 == -1);

}