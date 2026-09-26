#include "sra.h"

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