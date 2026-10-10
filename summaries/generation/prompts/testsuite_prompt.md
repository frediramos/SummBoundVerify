The summaries in `{{summaries}}/<function>/` each pass the fuzzer, which
checks one call at a time. Programs that use them together must work too:
the testsuite in `{{tests}}` runs them, with its helpers in `{{helpers}}`.

The functions' manual pages are:

{{manuals}}

The Symbolic Reflection API that the summaries use is documented in
`src/summboundverify/api/sra.h`.

{{report}}

Fix the summaries so that the tests pass. Every summary you change is fuzzed
again, and must still pass.
