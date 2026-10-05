#include "sra.h"

#define SIZE 3

int main(){
  
  int ret1 = __file_create("abc");
  __sra_assert(ret1 == 1);
  
  int ret2 = __file_open("abc", "r");
  __sra_assert(ret2 == 3);

  int ret3 = __file_close(ret2);
  __sra_assert(ret3 == 0);

}