char fold_tolower_strcasecmp(char c)
{
  char c1;
  if (__is_certain(_AND_(_GE_(c, 65), _LE_(c, 90))))
  {
    c1 = c + (97 - 65);
  }
  else
  {
    if (__is_certain(_NOT_(_AND_(_GE_(c, 65), _LE_(c, 90)))))
    {
      c1 = c;
    }
    else
    {
      __push_pc();
      __assume(_AND_(_GE_(c, 65), _LE_(c, 90)));
      c1 = c + (97 - 65);
      char aux1 = c1;
      __pop_pc();
      __push_pc();
      __assume(_NOT_(_AND_(_GE_(c, 65), _LE_(c, 90))));
      c1 = c;
      char aux2 = c1;
      __pop_pc();
      c1 = _ITE_VAR_(_AND_(_GE_(c, 65), _LE_(c, 90)), aux1, aux2);
    }
  }
  return c1;
}

int fold_strcased_strcasecmp(char *s1, char *s2)
{
  int b;
  unsigned char var1 = *s1;
  unsigned char var2 = *s2;
  unsigned char var3 = fold_tolower_strcasecmp(var1);
  unsigned char var4 = fold_tolower_strcasecmp(var2);
  if (__is_certain(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0'))))
  {
    b = var3 - var4;
  }
  else
  {
    if (__is_certain(_NOT_(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0')))))
    {
      if (__is_certain(_NEQ_(var3, var4)))
      {
        b = var3 - var4;
      }
      else
      {
        if (__is_certain(_NOT_(_NEQ_(var3, var4))))
        {
          b = fold_strcased_strcasecmp(s1 + 1, s2 + 1);
        }
        else
        {
          __push_pc();
          __assume(_NEQ_(var3, var4));
          b = var3 - var4;
          int aux1 = b;
          __pop_pc();
          __push_pc();
          __assume(_NOT_(_NEQ_(var3, var4)));
          b = fold_strcased_strcasecmp(s1 + 1, s2 + 1);
          int aux2 = b;
          __pop_pc();
          b = _ITE_VAR_(_NEQ_(var3, var4), aux1, aux2);
        }
      }
    }
    else
    {
      __push_pc();
      __assume(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0')));
      b = var3 - var4;
      int aux3 = b;
      __pop_pc();
      __push_pc();
      __assume(_NOT_(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0'))));
      if (__is_certain(_NEQ_(var3, var4)))
      {
        b = var3 - var4;
      }
      else
      {
        if (__is_certain(_NOT_(_NEQ_(var3, var4))))
        {
          b = fold_strcased_strcasecmp(s1 + 1, s2 + 1);
        }
        else
        {
          __push_pc();
          __assume(_NEQ_(var3, var4));
          b = var3 - var4;
          int aux1 = b;
          __pop_pc();
          __push_pc();
          __assume(_NOT_(_NEQ_(var3, var4)));
          b = fold_strcased_strcasecmp(s1 + 1, s2 + 1);
          int aux2 = b;
          __pop_pc();
          b = _ITE_VAR_(_NEQ_(var3, var4), aux1, aux2);
        }
      }
      int aux4 = b;
      __pop_pc();
      b = _ITE_VAR_(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0')), aux3, aux4);
    }
  }
  return b;
}

int strcasecmp(char *s1, char *s2)
{
  int ret;
  int var1 = fold_strcased_strcasecmp(s1, s2);
  ret = var1;
  return ret;
}
