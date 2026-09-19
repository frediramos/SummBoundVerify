typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_memw_memcpy(char *s, list_t lst, cnstr_t pc)
{
  if (__is_certain(__lst_empty(lst)))
  {
  }
  else
  {
    if (__is_certain(_NOT_(__lst_empty(lst))))
    {
      list_t var1 = __lst_hd(lst);
      list_t var2 = __lst_tl(lst);
      __cond_write(s, var1, pc);
      unfold_memw_memcpy(s + 1, var2, pc);
    }
    else
    {
      __push_pc();
      __assume(__lst_empty(lst));
      unfold_memw_memcpy(s, lst, _AND_(pc, __lst_empty(lst)));
      __pop_pc();
      __push_pc();
      __assume(_NOT_(__lst_empty(lst)));
      unfold_memw_memcpy(s, lst, _AND_(pc, _NOT_(__lst_empty(lst))));
      __pop_pc();
    }
  }
}

list_t fold_memseg_memcpy(char *s, unsigned int n)
{
  list_t lst;
  if (__is_certain(_ULE_(n, 0)))
  {
    lst = __lst_mk();
  }
  else
  {
    if (__is_certain(_NOT_(_ULE_(n, 0))))
    {
      char var1 = *s;
      list_t var2 = fold_memseg_memcpy(s + 1, n - 1);
      lst = __lst_cons(var1, var2);
      __assert(_NOT_(__lst_empty(lst)));
    }
    else
    {
      __push_pc();
      __assume(_ULE_(n, 0));
      lst = __lst_mk();
      list_t aux1 = lst;
      __pop_pc();
      __push_pc();
      __assume(_NOT_(_ULE_(n, 0)));
      char var1 = *s;
      list_t var2 = fold_memseg_memcpy(s + 1, n - 1);
      lst = __lst_cons(var1, var2);
      __assert(_NOT_(__lst_empty(lst)));
      list_t aux2 = lst;
      __pop_pc();
      lst = _ITE_VAR_(_ULE_(n, 0), aux1, aux2);
    }
  }
  return lst;
}

void *memcpy(void *dest, void *src, unsigned int n)
{
  void *ret;
  list_t var1 = fold_memseg_memcpy(src, n);
  __allocd(dest, n);
  unfold_memw_memcpy(dest, var1, TRUE);
  ret = dest;
  return ret;
}
