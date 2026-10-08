typedef unsigned int size_t;
typedef unsigned int cnstr_t;
#define FALSE 0
#define TRUE 1

int create_and_delete(const char *path)
{
  int ret = __file_create(path);
  if (ret != 1)
  {
    return -1;
  }
  ret = __file_delete(path);
  return ret;
}
