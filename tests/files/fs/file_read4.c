#include "sra.h"
#include "utils.h"

#define SIZE 5

int main(){

  char s1[SIZE];
  char s2[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
    s2[i] = __sym_var_array("s2", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';
  s2[SIZE-1] = '\0';

  valid_fname(s1);
  valid_fname(s2);

  int ret1 = __file_create(s1);
  __sra_assert(ret1 == 1);
  
  int fd1 = __file_open(s1, "r+");
  int fd2 = __file_open(s2, "r+");

  __sra_assert(fd1 == 3);
  __sra_assert(fd2 == 4);

  char buffer[5];

  int written = __file_write(fd2, "abc", 3);
  int read = __file_read(fd1, buffer, 3);

  __sra_assert(written == 3);

  cnstr_t eq = eq_strings(s1, s2, SIZE);
  __assume(eq);
  __sra_assert(_EQ_(read, 3));
  
  __sra_assert(_EQ_(buffer[0], 'a'));
  __sra_assert(_EQ_(buffer[1], 'b'));
  __sra_assert(_EQ_(buffer[2], 'c'));

}