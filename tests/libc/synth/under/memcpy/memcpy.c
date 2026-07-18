typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_memw_memcpy(char *s, list_t lst)
{
  if (lst_empty(lst))
  {
  }
  else
  {
    list_t var1 = lst_hd(lst);
    list_t var2 = lst_tl(lst);
    *s = var1;
    unfold_memw_memcpy(s + 1, var2);
  }
}

list_t fold_memseg_memcpy(char *s, unsigned int n)
{
  if (is_certain(_ULE_(n, 0)))
  {
    list_t lst = lst_mk();
    return lst;
  }
  else
  {
    assume(_NOT_(_ULE_(n, 0)));
    char var1 = *s;
    list_t var2 = fold_memseg_memcpy(s + 1, n - 1);
    list_t lst = lst_cons(var1, var2);
    _assert(_NOT_(lst_empty(lst)));
    return lst;
  }
}

void *memcpy(void *dest, void *src, unsigned int n)
{
  list_t var1 = fold_memseg_memcpy(src, n);
  allocd(dest, n);
  unfold_memw_memcpy(dest, var1);
  void *ret = dest;
  return ret;
}

