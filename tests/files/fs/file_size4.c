#include "sra.h"
#include "utils.h"

#define SIZE 3

int main(){
  
  char s1[SIZE];
  char s2[SIZE];
  char s3[SIZE];
  char s4[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
    s2[i] = __sym_var_array("s2", i, CHAR_SIZE);
    s3[i] = __sym_var_array("s3", i, CHAR_SIZE);
    s4[i] = __sym_var_array("s4", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';
  s2[SIZE-1] = '\0';
  s3[SIZE-1] = '\0';
  s4[SIZE-1] = '\0';

  valid_fname(s1);
  valid_fname(s2);
  valid_fname(s3);
  valid_fname(s4);

  int ret1 = __file_create(s1);
  int ret2 = __file_create(s2);
  __sra_assert(ret1 == 1);
  __sra_assert(ret2 == 1);

  int fd1 = __file_open(s3, "r+");
  int fd2 = __file_open(s4, "r+");
  __sra_assert(fd1 == 3);
  __sra_assert(fd2 == 4);
  
  ssize_t written = __file_write(fd1, "abc", 3);
  ssize_t size = __file_size(fd1);
  
  __sra_assert(written == 3);

  cnstr_t eq1 = eq_strings(s3, s1, SIZE);
  cnstr_t eq2 = eq_strings(s3, s2, SIZE);

  __assume(_OR_(eq1, eq2));

  __sra_assert(_EQ_(size, 3));

}