int concrete_strcasecmp(char* s1, char* s2){
  	while (1){
     	unsigned char u1 = (unsigned char) _tolower((int)*s1);
      	unsigned char u2 = (unsigned char) _tolower((int)*s2);

        s1++;
        s2++;
   	
		if (u1 != u2) return u1-u2;
      	if (u1 == '\0') return 0;   
    }

  	return 0;
}