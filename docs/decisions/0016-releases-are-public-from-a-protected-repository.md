---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Releases are public, from a protected repository

:::{decision}
:chooses: OPT_0016_PUBLIC
:resolves: Q_WHEEL_ACCESS
:driven_by: REQ_RELEASE_TRUST, REQ_NO_SECRETS_IN_TREE, REQ_ONE_PACKAGE
:::

## Context and Problem Statement

wyatt, 2026-11-08, asked whether to make this repository public or to authenticate wheel
downloads, and whether to protect main and the version tags: "yep, protect main and tag
as you see fit. and then sure, public is fine after a thorough scan". An adopting
repository downloads the release wheel in CI, and the release is only as trustworthy as
the branch and the tags it is built from.

## Decision Drivers

- An adopting repository installs the package with no credential to leak
- What becomes public was scanned for secrets first
- Nobody but a maintainer can create or move a version tag, and nothing reaches main
  without passing the check

## Considered Options

:::{opt} Make the repository public after a scan, and protect main and the version tags
:id: OPT_0016_PUBLIC
Good, because an adopter's CI downloads the wheel with no token, and GitHub's secret
scanning and push protection apply to public repositories at no cost. Bad, because every
commit, pull request and CI log is public, so the scan has to cover all of them first.
:::

:::{opt} Keep it private and authenticate downloads with a token
:id: OPT_0016_TOKEN
Good, because the code stays private. Bad, because every adopter holds a token that can
read this repository, and rulesets on a private repository need a paid plan.
:::

## Decision Outcome

Chosen option: {need}`OPT_0016_PUBLIC`, because it removes the credential from every
adopting repository and was approved after a clean scan.

## Consequences

- Good, because the scan covered every blob and commit message on every ref, every pull
  request with its comments, and every CI log, and found nothing to remove.
- Good, because main refuses deletion and force pushes, takes changes only by pull request,
  and requires the check job to pass, with no bypass; version tags can be created, moved
  or deleted only by a repository admin.
- Bad, because required approvals stay at zero and code-owner review stays off while one
  maintainer approves every pull request; a second maintainer brings both back.
