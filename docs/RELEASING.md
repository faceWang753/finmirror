# Releasing FinMirror to PyPI

The repository contains a release-triggered Trusted Publishing workflow, but adding the
workflow does **not** publish a package. Complete the controls below before publishing the
first release.

## One-time security setup

1. Create the `pypi` GitHub environment and require a trusted maintainer's manual approval.
2. In PyPI's pending Trusted Publisher form, register project `finmirror`, owner
   `faceWang753`, repository `finmirror`, workflow `release.yml`, and environment `pypi`.
3. Protect release tags and review every change to `.github/workflows/release.yml` as if it
   changed a publishing credential. Do not add a long-lived PyPI API token.

## Release checklist

1. Confirm the working tree is clean and CI passes on the exact release commit.
2. Set `__version__` in `src/finmirror/__init__.py`, update `CHANGELOG.md`, and update
   `CITATION.cff` with the same released version and date.
3. Locally run `python -m build` and `python -m twine check --strict dist/*`.
4. Create a GitHub release whose tag is exactly `v<version>`, for example `v0.2.0`.
5. Review the workflow's build evidence, then approve the protected `pypi` environment.
6. Verify the PyPI file hashes, provenance attestations, project links, and a clean-environment
   `python -m pip install finmirror` smoke test before announcing availability.

The workflow builds from the released tag, refuses a tag/source-version mismatch, checks
both distributions, smoke-tests the wheel, and gives only the publish job the short-lived
OIDC permission. PyPI's official publishing action generates attestations by default.
