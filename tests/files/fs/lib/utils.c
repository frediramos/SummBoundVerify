#include "utils.h"

cnstr_t eq_strings(const char* s1, const char* s2, int n){
  cnstr_t eq = 1; //True
  for (int i = 0; i < n; i++){
    eq = _AND_(eq, _EQ_(s1[i], s2[i]));
  }
  return eq;
}

// Assume s to be a valid filename
void valid_fname(const char* s){
  cnstr_t c = _NEQ_(s[0], '\0');
  __assume(c);
}
