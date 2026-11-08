---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Tests prove what no corpus mutation can show

:::{decision}
:chooses: OPT_0015_NAMED_TESTS
:resolves: Q_NON_CORPUS_PROOF
:driven_by: REQ_PROVEN_BY_TEST, REQ_FIXTURE_PER_INVARIANT
:::

## Context and Problem Statement

Every enforced requirement is proven by a negative fixture, a mutation of this corpus
that the check rejects. Some requirements are about what the package does outside the
corpus: that init produces a passing repository, that the hook refuses a path, that the
README's commands work. No corpus mutation can show those, and an unproven requirement
is a claim.

## Decision Drivers

- Every enforced requirement keeps a proof the check runs
- The proof names the requirement it proves, as a fixture does
- No new test framework enters the pinned toolchain

## Considered Options

:::{opt} Standard-library tests that declare the requirements they prove
:id: OPT_0015_NAMED_TESTS
Good, because the fixture audit counts a test that names a requirement as its proof
once the test runs and passes, and `unittest` needs no new dependency. Bad, because a test
can name a requirement it does not really exercise; review judges that, as it does for
fixtures.
:::

:::{opt} Exempt such requirements from the audit
:id: OPT_0015_EXEMPT
Good, because nothing is built. Bad, because the requirement is then enforced by nothing
the check runs.
:::

:::{opt} Express each as a corpus mutation anyway
:id: OPT_0015_FIXTURES_ONLY
Good, because there is one kind of proof. Bad, because the mutations would have to fake
the package's behaviour, and would prove the fake.
:::

## Decision Outcome

Chosen option: {need}`OPT_0015_NAMED_TESTS`, because it keeps every enforced requirement
proven by something the check runs.

## Consequences

- Good, because the audit reads one declaration per test, the way it reads `expect` in a
  fixture.
- Bad, because the check gets slower by the tests' runtime; init and README tests build a
  wheel once and reuse it.
