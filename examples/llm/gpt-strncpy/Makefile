SHELL := /bin/bash

CONCRETE := concrete.c
SUMMARY  := summ.c
TEST     := validation.c

CMD := summbv -func $(CONCRETE) -summ $(SUMMARY) --maxvalue 5 --compile x86 -o $(TEST)

.PHONY: gen run

gen:
	$(CMD)

run:
	$(CMD) -run

clean:
	$(RM) *.o *.test *.json $(TEST)