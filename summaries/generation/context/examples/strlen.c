/*Summary for libc's strlen*/

#include "sra.h"

size_t strlen(char* s){
 	
 	int i = 0;
 	char char_zero = '\0';

 	//Calculate max string length
 	while(__is_symbolic(s[i]) || s[i] != '\0'){
		i++;
 	}

	int len = i;
	symbolic ret = __sym_var(INT_SIZE);
	cnstr_t ret_cnstr = _EQ_(ret, len);

	//Build recursive ITE constraint
	for(i = len-1; i >= 0; i--){

		if(__is_symbolic(s[i])){

			cnstr_t c_eq_zero = _EQ_(s[i], char_zero);
			cnstr_t ret_eq_i = _EQ_(ret, i);

			ret_cnstr = _ITE_(c_eq_zero, ret_eq_i, ret_cnstr);
			
		}
	}

	__assume(ret_cnstr);
	return ret;
}