#include "sra.h"

int main(){

  // A negative limit is invalid
  __sra_assert(__file_set_max_fds(-1) == -1);

  // Without a limit set, many descriptors can be open
  __file_create("abc");
  for (int i = 0; i < 40; i++)
    __sra_assert(__file_open("abc", "r") == 3 + i);
}
