#include "sra.h"

#define SIZE 5

cnstr_t eq_strings(const char* s1, const char* s2, int n){
  cnstr_t eq = 1; //True
  for (int i = 0; i < n; i++){
    eq = _AND_(eq, _EQ_(s1[i], s2[i]));
  }
  return eq;
}


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

  int ret1 = __file_create(s1);
  int ret2 = __file_create(s2);
  __assert(ret1 == 1);
  __assert(ret2 == 1);
  
  int fd1 = __file_open(s3, "r+");
  int fd2 = __file_open(s4, "r+");

  __assert(fd1 == 3);
  __assert(fd2 == 4);

  char buffer[5];

  ssize_t set = __file_set_offset(fd1, 2);
  __assert(set == 2);

  int written = __file_write(fd1, "abc", 3);
  int read = __file_read(fd2, buffer, 5);

  __assert(written == 3);

  cnstr_t eq1 = eq_strings(s1, s3, SIZE);
  cnstr_t eq2 = eq_strings(s4, s3, SIZE);

  __assume(eq1);
  __assume(eq2);

  __assert(_EQ_(read, 5));
  
  __assert(_EQ_(buffer[0], '\0'));
  __assert(_EQ_(buffer[1], '\0'));
  __assert(_EQ_(buffer[2], 'a'));
  __assert(_EQ_(buffer[3], 'b'));
  __assert(_EQ_(buffer[4], 'c'));

}