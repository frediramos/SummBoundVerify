#include "sra.h"
#include "utils.h"

#define SIZE 5

int main(){

  char s1[SIZE];

  // Fill with symbolic bytes
  for (int i = 0; i < SIZE; i++){
    s1[i] = __sym_var_array("s1", i, CHAR_SIZE);
  }

  // Concrete null byte
  s1[SIZE-1] = '\0';

  valid_fname(s1);

  int ret1 = __file_create("file");
  __sra_assert(ret1 == 1);
  
  int fd1 = __file_open("file", "r+");
  int fd2 = __file_open(s1, "r+");

  __sra_assert(fd1 == 3);
  __sra_assert(fd2 == 4);

  char buffer[5];

  int written = __file_write(fd1, "abc", 3);
  int read = __file_read(fd2, buffer, 3);

  __sra_assert(written == 3);

  cnstr_t eq = eq_strings(s1, "file", SIZE);
  __assume(eq);
  __sra_assert(_EQ_(read, 3));
  
  __sra_assert(_EQ_(buffer[0], 'a'));
  __sra_assert(_EQ_(buffer[1], 'b'));
  __sra_assert(_EQ_(buffer[2], 'c'));

}