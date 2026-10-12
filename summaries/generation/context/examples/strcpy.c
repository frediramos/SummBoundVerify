/*Summary for libc's strcpy*/

#include "sra.h"

char* strcpy(char* dest, char* source){
	int i = 0;
	char zero = '\0';

	while(1){
		if(__is_symbolic(source[i])){
			
			if(!__is_sat(_NEQ_(source[i], zero))){
				break;
			}
			
			else{
				__assume(_NEQ_(source[i], zero));
			}
		}

		else if(source[i] == '\0'){
			break;
		}
		dest[i] = source[i];
		i++;
	}

	dest[i] = '\0';
	return dest;

}