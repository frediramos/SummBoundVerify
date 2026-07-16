char fold_tolower_strcasecmp(char c)
{
  if (is_certain(_AND_(_GE_(c, 65), _LE_(c, 90))))
  {
    char c1 = c + (97 - 65);
    return c1;
  }
  else
  {
    assume(_NOT_(_AND_(_GE_(c, 65), _LE_(c, 90))));
    char c1 = c;
    return c1;
  }
}

int fold_strcased_strcasecmp(char *s1, char *s2)
{
  unsigned char var1 = *s1;
  unsigned char var2 = *s2;
  unsigned char var3 = fold_tolower_strcasecmp(var1);
  unsigned char var4 = fold_tolower_strcasecmp(var2);
  if (is_certain(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0'))))
  {
    int b = var3 - var4;
    return b;
  }
  else
  {
    assume(_NOT_(_OR_(_EQ_(var1, '\0'), _EQ_(var2, '\0'))));
    if (is_certain(_NEQ_(var3, var4)))
    {
      int b = var3 - var4;
      return b;
    }
    else
    {
      assume(_NOT_(_NEQ_(var3, var4)));
      int b = fold_strcased_strcasecmp(s1 + 1, s2 + 1);
      return b;
    }
  }
}

int strcasecmp(char *s1, char *s2)
{
  int var1 = fold_strcased_strcasecmp(s1, s2);
  int ret = var1;
  return ret;
}

