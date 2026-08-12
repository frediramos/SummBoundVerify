int fold_str_strlen(char *s)
{
  char var1 = *s;
  if (__is_certain(_EQ_(var1, '\0')))
  {
    int n = 0;
    return n;
  }
  else
  {
    __assume(_NOT_(_EQ_(var1, '\0')));
    int var2 = fold_str_strlen(s + 1);
    int n = var2 + 1;
    return n;
  }
}

int strlen(char *s)
{
  int var1 = fold_str_strlen(s);
  int ret = var1;
  return ret;
}

