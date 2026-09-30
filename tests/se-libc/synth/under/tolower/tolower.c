int fold_tolower_tolower(int c)
{
  if (__is_certain(_AND_(_GE_(c, 65), _LE_(c, 90))))
  {
    int c1 = c + (97 - 65);
    return c1;
  }
  else
  {
    __assume(_NOT_(_AND_(_GE_(c, 65), _LE_(c, 90))));
    int c1 = c;
    return c1;
  }
}

int tolower(int c)
{
  int var1 = fold_tolower_tolower(c);
  int ret = var1;
  return ret;
}

