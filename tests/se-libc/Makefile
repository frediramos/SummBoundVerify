DIR := $(notdir $(CURDIR))
SUBDIRS := $(shell find */**/* -type d | sort -n)

RED     := \033[31m
GREEN   := \033[32m
YELLOW  := \033[33m
BLUE    := \033[34m
MAGENTA := \033[35m
RESET   := \033[0m

.PHONY: test test-run clean

test:
	$(call run,test)
	
test-run:
	$(call run,test-run)

clean: $(SUBDIRS:%=clean/%)

clean/%:
	$(MAKE) -C $* -s clean


define run
	@passed=0; failed=0; \
	echo "-- $(YELLOW)$(DIR)$(RESET) --"; \
	for d in $(SUBDIRS); do \
		printf "$(BLUE)$$d$(RESET) - "; \
		log=$$(mktemp); \
		if $(MAKE) -C $$d $(1) >$$log 2>&1; then \
			printf "$(GREEN)PASS$(RESET)\n"; \
			passed=$$((passed + 1)); \
		else \
			printf "$(RED)FAIL$(RESET)\n"; \
			cat $$log; \
			failed=$$((failed + 1)); \
		fi; \
		rm -f $$log; \
	done; \
	echo; \
	echo "$(GREEN)Passed:$(RESET) $$passed"; \
	echo "$(RED)Failed:$(RESET) $$failed"; \
	test $$failed -eq 0
endef