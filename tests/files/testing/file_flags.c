#include "sra.h"

#define SIZE 3

int main(){
  
  int ret = __file_create("abc");

  int fd1 = __file_open("abc", "r");
  int fd2 = __file_open("abc", "w");
  int fd3 = __file_open("abc", "a");
  int fd4 = __file_open("abc", "r+");
  int fd5 = __file_open("abc", "w+");
  int fd6 = __file_open("abc", "a+");

  int flags1 = __file_flags(fd1);
  int flags2 = __file_flags(fd2);
  int flags3 = __file_flags(fd3);
  int flags4 = __file_flags(fd4);
  int flags5 = __file_flags(fd5);
  int flags6 = __file_flags(fd6);

  __assert(flags1 == 0);
  __assert(flags2 == 577);
  __assert(flags3 == 1089);
  __assert(flags4 == 2);
  __assert(flags5 == 578);
  __assert(flags6 == 1090);
}