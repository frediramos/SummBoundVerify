#include "sra.h"

#define SIZE 3

int main(){
  
  int ret = __file_create("abc");
  int fd1 = __file_open("abc", "r+");
  __assert(ret == 1);
  __assert(fd1 == 3);

  int fd2 = __file_dup(fd1);
  __assert(fd2 == 4);

  int count = __file_write(fd1, "abc", 3);
  __assert(count == 3);

  ssize_t offset1 = __file_offset(fd1);
  ssize_t offset2 = __file_offset(fd2);

  __assert(offset1 == 3);
  __assert(offset2 == 3);

  __file_set_offset(fd1, 0);
  __file_set_offset(fd2, 0);
  
  offset1 = __file_offset(fd1);
  offset2 = __file_offset(fd2);

  __assert(offset1 == 0);
  __assert(offset2 == 0);

  char buffer1[5];
  char buffer2[5];
  
  __file_read(fd1, buffer1, 3);
  __assert(buffer1[0] == 'a');
  __assert(buffer1[1] == 'b');
  __assert(buffer1[2] == 'c');
  
  offset2 = __file_offset(fd2);
  __assert(offset2 == 3);

  __file_set_offset(fd2, 0);
  __file_read(fd2, buffer2, 3);
  __assert(buffer2[0] == 'a');
  __assert(buffer2[1] == 'b');
  __assert(buffer2[2] == 'c');
  
}