typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_cstr_strdup(char *s, list_t lst, cnstr_t pc)
{
  if (is_certain(lst_empty(lst)))
  {
    char var1 = '\0';
    cond_write(s, var1, pc);
  }
  else
  {
    if (is_certain(_NOT_(lst_empty(lst))))
    {
      list_t var2 = lst_hd(lst);
      list_t var3 = lst_tl(lst);
      cond_write(s, var2, pc);
      assume(_NEQ_(var2, '\0'));
      unfold_cstr_strdup(s + 1, var3, pc);
    }
    else
    {
      push_pc();
      assume(lst_empty(lst));
      unfold_cstr_strdup(s, lst, _AND_(pc, lst_empty(lst)));
      pop_pc();
      push_pc();
      assume(_NOT_(lst_empty(lst)));
      unfold_cstr_strdup(s, lst, _AND_(pc, _NOT_(lst_empty(lst))));
      pop_pc();
    }
  }
}

list_t fold_cstr_strdup(char *s)
{
  list_t lst;
  char var1 = *s;
  if (is_certain(_EQ_(var1, '\0')))
  {
    lst = lst_mk();
  }
  else
  {
    if (is_certain(_NOT_(_EQ_(var1, '\0'))))
    {
      list_t var2 = fold_cstr_strdup(s + 1);
      lst = lst_cons(var1, var2);
      _assert(_NOT_(lst_empty(lst)));
    }
    else
    {
      push_pc();
      assume(_EQ_(var1, '\0'));
      lst = lst_mk();
      list_t aux1 = lst;
      pop_pc();
      push_pc();
      assume(_NOT_(_EQ_(var1, '\0')));
      list_t var2 = fold_cstr_strdup(s + 1);
      lst = lst_cons(var1, var2);
      _assert(_NOT_(lst_empty(lst)));
      list_t aux2 = lst;
      pop_pc();
      lst = _ITE_VAR_(_EQ_(var1, '\0'), aux1, aux2);
    }
  }
  return lst;
}

char *strdup(char *str)
{
  char *ret;
  list_t var1 = fold_cstr_strdup(str);
  int var2 = lst_len(var1);
  char *dest = mem_alloc((var2 + 1) * sizeof(char));
  unfold_cstr_strdup(dest, var1, TRUE);
  ret = dest;
  return ret;
}
