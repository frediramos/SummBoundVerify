int fold_str(char *s)
{
  int n;
  char var1 = *((char *) s);
  if (is_certain(_EQ_(var1, '\0')))
  {
    n = 0;
  }
  else
  {
    if (is_certain(_NOT_(_EQ_(var1, '\0'))))
    {
      int var2 = fold_str(s + 1);
      n = var2 + 1;
    }
    else
    {
      push_pc();
      assume(_EQ_(var1, '\0'));
      n = 0;
      int aux1 = n;
      pop_pc();
      push_pc();
      assume(_NOT_(_EQ_(var1, '\0')));
      int var2 = fold_str(s + 1);
      n = var2 + 1;
      int aux2 = n;
      pop_pc();
      n = _ITE_VAR_(_EQ_(var1, '\0'), aux1, aux2);
    }
  }
  return n;
}

int strlen(char *s)
{
  int ret;
  int var1 = fold_str(s);
  ret = var1;
  return ret;
}

