int fold_tolower_tolower(int c)
{
  int c1;
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
      int aux1 = c1;
      __pop_pc();
      __push_pc();
      __assume(_NOT_(_AND_(_GE_(c, 65), _LE_(c, 90))));
      c1 = c;
      int aux2 = c1;
      __pop_pc();
      c1 = _ITE_VAR_(_AND_(_GE_(c, 65), _LE_(c, 90)), aux1, aux2);
    }
  }
  return c1;
}

int tolower(int c)
{
  int ret;
  int var1 = fold_tolower_tolower(c);
  ret = var1;
  return ret;
}

