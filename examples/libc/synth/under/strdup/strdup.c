typedef unsigned int size_t;
typedef unsigned int cnstr_t;
typedef unsigned int list_t;
#define FALSE 0
#define TRUE 1

void unfold_cstr_strdup(char *s, list_t lst)
{
  if (lst_empty(lst))
  {
    char var1 = '\0';
    *s = var1;
  }
  else
  {
    list_t var2 = lst_hd(lst);
    list_t var3 = lst_tl(lst);
    *s = var2;
    assume(_NEQ_(var2, '\0'));
    unfold_cstr_strdup(s + 1, var3);
  }
}

list_t fold_cstr_strdup(char *s)
{
  char var1 = *s;
  if (is_certain(_EQ_(var1, '\0')))
  {
    list_t lst = lst_mk();
    return lst;
  }
  else
  {
    assume(_NOT_(_EQ_(var1, '\0')));
    list_t var2 = fold_cstr_strdup(s + 1);
    list_t lst = lst_cons(var1, var2);
    _assert(_NOT_(lst_empty(lst)));
    return lst;
  }
}

char *strdup(char *str)
{
  list_t var1 = fold_cstr_strdup(str);
  int var2 = lst_len(var1);
  char *dest = mem_alloc((var2 + 1) * sizeof(char));
  unfold_cstr_strdup(dest, var1);
  char *ret = dest;
  return ret;
}

