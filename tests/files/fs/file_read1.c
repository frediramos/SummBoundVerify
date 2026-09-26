#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("file");
  __assert(ret1 == 1);
  
  int fd1 = __file_open("file", "r+");
  int fd2 = __file_open("file", "r+");
  __assert(fd1 == 3);
  __assert(fd2 == 4);

  char buffer[5];

  int written = __file_write(fd1, "abc", 3);
  int read = __file_read(fd2, buffer, 3);

  __assert(written == 3);
  __assert(read == 3);

  __assert(buffer[0] == 'a');
  __assert(buffer[1] == 'b');
  __assert(buffer[2] == 'c');

}