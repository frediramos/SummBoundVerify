#include "sra.h"

#define SIZE 3

int main(){
  
  char s1[SIZE];
  char s2[SIZE];
  char s3[SIZE];
  char s4[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }
  
  for (int i = 0; i < SIZE; i++){
    s2[i] = __sym_var_array("s2", i, CHAR_SIZE);
  }

  for (int i = 0; i < SIZE; i++){
    s3[i] = __sym_var_array("s3", i, CHAR_SIZE);
  }
  
  for (int i = 0; i < SIZE; i++){
    s4[i] = __sym_var_array("s4", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';
  s2[SIZE-1] = '\0';
  s3[SIZE-1] = '\0';
  s4[SIZE-1] = '\0';

  int ret1 = __file_create(s1);
  __assert(ret1 == 1);
  
  int ret2 = __file_create(s2);
  __assert(ret2 == 1);

  int ret3 = __file_open(s3, "r+");
  __assert(ret3 == 3);
  
  int ret4 = __file_open(s4, "r+");
  __assert(ret4 == 4);

}