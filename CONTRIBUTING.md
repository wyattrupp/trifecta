# Contributing

Thank you for helping. This repository is its own example: its documents describe the
toolchain, and the toolchain checks them. A change lands when `make check` passes.

## Reporting

- **A bug or a request:** open an issue from one of the templates. For a bug, give the
  release or commit, the command, and the findings `trifecta check` printed, each with
  the requirement ID it begins with.
- **A vulnerability:** do not open an issue; follow `SECURITY.md`.
- **A question:** open a blank issue.

## Setting up

You need Python 3.12 or later, `git` and `make`. From a clone:

```sh
make setup   # the hashed lock, this package from src/, and Vale for this platform
make check   # build, validate, lint, and run the tests
```

Without `make`, `README.md` lists the same commands as `trifecta`.

## Making a change

1. **Start from a requirement.** The requirements live in the RFCs under `docs/rfcs/`. A
   change in behaviour starts as a document from `trifecta new`: an RFC for a new
   requirement, a MADR per choice, a design doc for the components, then a plan. Small
   fixes that change no requirement need none of these.
2. **Prove it.** A requirement a component enforces needs a negative fixture under
   `tests/fixtures/`, and a test under `tests/` declares the requirements it proves. Run
   `make fixtures` after changing a rule.
3. **Check it.** `make check BASE=main` also holds history: an accepted MADR does not
   change.
4. **Open a pull request** against `main` and fill in its template. CI runs the same
   check.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
`fix:`, `feat:`, `docs:`, `test:`, with a scope where it helps.

## Conduct

Everyone taking part follows `CODE_OF_CONDUCT.md`.

## Licence

By contributing, you agree that your contribution is licensed under the MIT License in
`LICENSE`.
