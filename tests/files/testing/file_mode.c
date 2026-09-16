#define NULL ((void*)0)
#define INT_SIZE (sizeof(int) * 8)
#define LONG_SIZE (sizeof(long) * 8)
#define CHAR_SIZE (sizeof(char) * 8)
#define PTR_SIZE (sizeof(void*) * 8)

#include <stdio.h>
#include <sys/types.h>

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
int __file_mode(int fd, mode_t* mode){ return 0; }
int __file_set_mode(int fd, mode_t mode){ return 0; }


#define SIZE 3

int main(){
  
  int ret = __file_create("abc");
  int fd = __file_open("abc");
  __assert(ret == 1);
  __assert(fd == 3);

  mode_t mode;

  __file_mode(fd, &mode);
  __assert(mode == 0644);

  __file_set_mode(fd, 0777);
  __file_mode(fd, &mode);

  __assert(mode == 0755);
}