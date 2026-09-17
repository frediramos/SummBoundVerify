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
int __file_open(char* filename, char* flags ){ return 0; }
ssize_t __file_write(int fd, const void* buffer, size_t count){ return 0; }
ssize_t __file_read(int fd, void* buffer, size_t count){ return 0; }
ssize_t __file_offset(int fd){ return 0; }
ssize_t __file_set_offset(int fd, size_t offset){ return 0; }
int __file_dup2(int fd1, int fd2){ return 0; }


#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  int ret2 = __file_create("def");
  int fd1 = __file_open("abc", "r+");
  int fd2 = __file_open("def", "r+");

  __assert(ret1 == 1);
  __assert(ret2 == 1);
  __assert(fd1 == 3);
  __assert(fd2 == 4);

  int count1 = __file_write(fd1, "123", 3);
  int count2 = __file_write(fd2, "456", 3);
  __assert(count1 == 3);
  __assert(count2 == 3);

  int fd3 = __file_dup2(fd1, fd2);
  __assert(fd2 == 4);
  
  __file_set_offset(fd2, 0);

  char buffer[5];
  
  __file_read(fd2, buffer, 3);
  __assert(buffer[0] == '1');
  __assert(buffer[1] == '2');
  __assert(buffer[2] == '3');

}