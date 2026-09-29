# Releasing

Publishing uses PyPI's **Trusted Publishing** (OIDC): GitHub proves its identity to PyPI at publish time,
so no API token is ever stored in this repo, in a GitHub secret, or anywhere else. `.github/workflows/publish.yml`
already does the automated half; the parts below need a human with a PyPI account.

## One-time setup (do this once, before the first release)

1. Create a PyPI account at [pypi.org/account/register](https://pypi.org/account/register/), if you don't
   have one. Enable 2FA -- PyPI requires it for publishing.
2. Go to [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/) and add a
   **pending publisher** (this works even though the `anchortest` project doesn't exist on PyPI yet):
   - PyPI project name: `anchortest`
   - Owner: `grant02339-ship-it`
   - Repository name: `anchortest`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. That's it -- no token to copy anywhere. The first successful run of the `publish` job creates the
   project on PyPI automatically.

## Cutting a release (every time after that)

```bash
cd ~/anchortest
# 1. bump the version
sed -i '' 's/version = "0.1.0"/version = "0.1.1"/' pyproject.toml   # pick the real next version
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
git push

# 2. tag and create a GitHub Release -- this is what triggers publish.yml
git tag v0.1.1
git push origin v0.1.1
gh release create v0.1.1 --title "v0.1.1" --generate-notes
```

`gh release create` triggers the `release: published` event, which runs the full pipeline: tests +
mutation check, build, then publish to PyPI. Watch it with `gh run watch` or at
`https://github.com/grant02339-ship-it/anchortest/actions`.

## Sanity check after the first publish

```bash
pip install anchortest
python -c "import anchortest; print(anchortest.__version__)"
```
