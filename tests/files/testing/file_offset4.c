#include "sra.h"

#define SIZE 3

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
  s4[SIZE-1] = '\0';

  // File names cannot be empty
  __assume(_NEQ_(s1[0], 0));
  __assume(_NEQ_(s2[0], 0));
  __assume(_NEQ_(s3[0], 0));
  __assume(_NEQ_(s4[0], 0));

  int ret1 = __file_create(s1);
  int ret2 = __file_create(s2);
  __assert(ret1 == 1);
  __assert(ret2 == 1);

  int fd1 = __file_open(s3, "r+");
  int fd2 = __file_open(s4, "r+");
  __assert(fd1 == 3);
  __assert(fd2 == 4);
  
  ssize_t written = __file_write(fd1, "abc", 3);
  ssize_t offset = __file_offset(fd2);
  
  __assert(written == 3);

  cnstr_t eq1 = eq_strings(s4, s1, SIZE);
  cnstr_t eq2 = eq_strings(s4, s2, SIZE);

  __assume(_OR_(eq1, eq2));

  __assert(_EQ_(offset, 0));

}