typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_memw_save_data(char *s, list_t lst)
{
  if (__lst_empty(lst))
  {
  }
  else
  {
    list_t var1 = __lst_hd(lst);
    list_t var2 = __lst_tl(lst);
    *s = var1;
    unfold_memw_save_data(s + 1, var2);
  }
}

list_t fold_memseg_save_data(char *s, unsigned int n)
{
  if (__is_certain(_ULE_(n, 0)))
  {
    list_t lst = __lst_mk();
    return lst;
  }
  else
  {
    __assume(_NOT_(_ULE_(n, 0)));
    char var1 = *s;
    list_t var2 = fold_memseg_save_data(s + 1, n - 1);
    list_t lst = __lst_cons(var1, var2);
    __assert(_NOT_(__lst_empty(lst)));
    return lst;
  }
}

int save_data(const char *path, const char *data, size_t len)
{
  int ret = __file_create(path);
  if (__is_certain(_NEQ_(ret, 1)))
  {
    return -1;
  }
  __assume(_EQ_(ret, 1));
  int fd = __file_open(path, "w");
  if (__is_certain(_LT_(fd, 0)))
  {
    return -1;
  }
  __assume(_GE_(fd, 0));
  list_t contents = fold_memseg_save_data((char *)data, len);
  int written = __file_write(fd, data, len);
  __file_close(fd);
  if (__is_certain(_NEQ_(written, len)))
  {
    return -1;
  }
  __assume(_EQ_(written, len));
  return 0;
}
