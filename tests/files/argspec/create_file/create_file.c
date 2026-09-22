typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

int create_file(const char *path)
{
  int ret = __file_create(path);
  return ret;
}
