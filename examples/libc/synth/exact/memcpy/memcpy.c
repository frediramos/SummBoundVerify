typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_memw_memcpy(char *s, list_t lst, cnstr_t pc)
{
  if (is_certain(lst_empty(lst)))
  {
  }
  else
  {
    if (is_certain(_NOT_(lst_empty(lst))))
    {
      list_t var1 = lst_hd(lst);
      list_t var2 = lst_tl(lst);
      cond_write(s, var1, pc);
      unfold_memw_memcpy(s + 1, var2, pc);
    }
    else
    {
      push_pc();
      assume(lst_empty(lst));
      unfold_memw_memcpy(s, lst, _AND_(pc, lst_empty(lst)));
      pop_pc();
      push_pc();
      assume(_NOT_(lst_empty(lst)));
      unfold_memw_memcpy(s, lst, _AND_(pc, _NOT_(lst_empty(lst))));
      pop_pc();
    }
  }
}

list_t fold_memseg_memcpy(char *s, unsigned int n)
{
  list_t lst;
  if (is_certain(_ULE_(n, 0)))
  {
    lst = lst_mk();
  }
  else
  {
    if (is_certain(_NOT_(_ULE_(n, 0))))
    {
      char var1 = *s;
      list_t var2 = fold_memseg_memcpy(s + 1, n - 1);
      lst = lst_cons(var1, var2);
      _assert(_NOT_(lst_empty(lst)));
    }
    else
    {
      push_pc();
      assume(_ULE_(n, 0));
      lst = lst_mk();
      list_t aux1 = lst;
      pop_pc();
      push_pc();
      assume(_NOT_(_ULE_(n, 0)));
      char var1 = *s;
      list_t var2 = fold_memseg_memcpy(s + 1, n - 1);
      lst = lst_cons(var1, var2);
      _assert(_NOT_(lst_empty(lst)));
      list_t aux2 = lst;
      pop_pc();
      lst = _ITE_VAR_(_ULE_(n, 0), aux1, aux2);
    }
  }
  return lst;
}

void *memcpy(void *dest, void *src, unsigned int n)
{
  void *ret;
  list_t var1 = fold_memseg_memcpy(src, n);
  allocd(dest, n);
  unfold_memw_memcpy(dest, var1, TRUE);
  ret = dest;
  return ret;
}
