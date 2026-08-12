typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_cstr_strdup(char *s, list_t lst, cnstr_t pc)
{
  if (__is_certain(__lst_empty(lst)))
  {
    char var1 = '\0';
    __cond_write(s, var1, pc);
  }
  else
  {
    if (__is_certain(_NOT_(__lst_empty(lst))))
    {
      list_t var2 = __lst_hd(lst);
      list_t var3 = __lst_tl(lst);
      __cond_write(s, var2, pc);
      __assume(_NEQ_(var2, '\0'));
      unfold_cstr_strdup(s + 1, var3, pc);
    }
    else
    {
      __push_pc();
      __assume(__lst_empty(lst));
      unfold_cstr_strdup(s, lst, _AND_(pc, __lst_empty(lst)));
      __pop_pc();
      __push_pc();
      __assume(_NOT_(__lst_empty(lst)));
      unfold_cstr_strdup(s, lst, _AND_(pc, _NOT_(__lst_empty(lst))));
      __pop_pc();
    }
  }
}

list_t fold_cstr_strdup(char *s)
{
  list_t lst;
  char var1 = *s;
  if (__is_certain(_EQ_(var1, '\0')))
  {
    lst = __lst_mk();
  }
  else
  {
    if (__is_certain(_NOT_(_EQ_(var1, '\0'))))
    {
      list_t var2 = fold_cstr_strdup(s + 1);
      lst = __lst_cons(var1, var2);
      __assert(_NOT_(__lst_empty(lst)));
    }
    else
    {
      __push_pc();
      __assume(_EQ_(var1, '\0'));
      lst = __lst_mk();
      list_t aux1 = lst;
      __pop_pc();
      __push_pc();
      __assume(_NOT_(_EQ_(var1, '\0')));
      list_t var2 = fold_cstr_strdup(s + 1);
      lst = __lst_cons(var1, var2);
      __assert(_NOT_(__lst_empty(lst)));
      list_t aux2 = lst;
      __pop_pc();
      lst = _ITE_VAR_(_EQ_(var1, '\0'), aux1, aux2);
    }
  }
  return lst;
}

char *strdup(char *str)
{
  char *ret;
  list_t var1 = fold_cstr_strdup(str);
  int var2 = __lst_len(var1);
  char *dest = __mem_alloc((var2 + 1) * sizeof(char));
  unfold_cstr_strdup(dest, var1, TRUE);
  ret = dest;
  return ret;
}
