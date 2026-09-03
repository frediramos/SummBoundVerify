#define NULL ((void*)0)
#define INT_SIZE (sizeof(int) * 8)
#define LONG_SIZE (sizeof(long) * 8)
#define CHAR_SIZE (sizeof(char) * 8)
#define PTR_SIZE (sizeof(void*) * 8)

#include <stdio.h>

typedef void *symbolic;
typedef int state_t;
typedef unsigned int cnstr_t;
typedef unsigned int result_t;
typedef unsigned int list_t;

symbolic __sym_var(size_t size) { return 0; }
symbolic __sym_var_named(char *name, size_t size) { return 0; }
symbolic __sym_var_array(char *name, size_t index, size_t size) { return 0; }

int __is_certain(cnstr_t cnstr) { return 0; }
int __is_sat(cnstr_t cnstr) { return 0; }
int __is_symbolic(symbolic var) { return 0; }

cnstr_t _EQ_(symbolic var1, symbolic var2) { return 0; }

void __assert(cnstr_t cnstr) { }
void __report_error(const char* filename, unsigned int line, const char* message){ return; }

int __file_create(char* filename){ return 0; }
int __file_exists(char* filename){ return 0; }
int __file_delete(char* filename){ return 0; }
int __file_open(char* filename){ return 0; }

ssize_t __file_write(int fd, const void* buffer, size_t count){ return 0; }


#define SIZE 4

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
  s1[SIZE -1] = '\0';
  s2[SIZE -1] = '\0';
  s3[SIZE -1] = '\0';
  s4[SIZE -1] = '\0';

  int ret1 = __file_create(s1);
  int ret2 = __file_create(s2);
  __assert(ret1 == 1);
  __assert(ret2 == 1);

  int fd1 = __file_open(s3);
  int fd2 = __file_open(s4);
  __assert(fd1 == 3);
  __assert(fd2 == 4);
  
  int count1 = __file_write(fd1, "abc", 3);
  int count2 = __file_write(fd2, "def", 3);
  int count3 = __file_write(fd1, "123", 3);
  
  __assert(count1 == 3);
  __assert(count2 == 3);
  __assert(count3 == 3);

}