# Repository settings

The GitHub settings this repository runs under, exported with `gh api`, so they are
reviewed like code. `rulesets.json` holds the rulesets on the default branch and on tags;
`security.json` holds visibility, secret scanning, Actions permissions, vulnerability
reporting and immutable releases; `environments.json` holds the `release` environment the
release is published from. They are the `spec` of COMP_REPO_PROTECTION in
`docs/design/0004-adopting-trifecta-in-another-repository.md`. `about.json` holds the
repository's description, homepage and topics, exported with
`gh api repos/wyattrupp/trifecta --jq '{description, homepage, topics}'`. GitHub is the source; after
changing a setting there, export it again here in the same pull request.
