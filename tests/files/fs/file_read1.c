#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("file");
  __sra_assert(ret1 == 1);
  
  int fd1 = __file_open("file", "r+");
  int fd2 = __file_open("file", "r+");
  __sra_assert(fd1 == 3);
  __sra_assert(fd2 == 4);

  char buffer[5];

  int written = __file_write(fd1, "abc", 3);
  int read = __file_read(fd2, buffer, 3);

  __sra_assert(written == 3);
  __sra_assert(read == 3);

  __sra_assert(buffer[0] == 'a');
  __sra_assert(buffer[1] == 'b');
  __sra_assert(buffer[2] == 'c');

}