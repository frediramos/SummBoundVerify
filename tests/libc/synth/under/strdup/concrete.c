char* concrete_strdup(char * str){
	int size = strlen(str);
	char* dest = (char*) malloc(size+1);
  	strcpy(dest, str);
	return dest;
}