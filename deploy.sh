#!/usr/bin/env bash
# One-time deploy of Daily Stop to GitHub Pages.
# Usage:  ./deploy.sh            (creates repo "daily-stop")
#         ./deploy.sh my-news    (custom repo name)
# Needs: git and the GitHub CLI (https://cli.github.com). On Windows, run in Git Bash.
set -euo pipefail

REPO="${1:-daily-stop}"

command -v git >/dev/null || { echo "Install git first: https://git-scm.com"; exit 1; }
command -v gh  >/dev/null || { echo "Install the GitHub CLI first: https://cli.github.com"; exit 1; }

if ! gh auth status >/dev/null 2>&1; then
  echo "Sign in to GitHub (a browser window will open)..."
  gh auth login --web --git-protocol https --scopes "repo,workflow"
fi
OWNER="$(gh api user --jq .login)"
echo "Deploying to $OWNER/$REPO"

# 1. Commit the project
if [ ! -d .git ]; then git init -q -b main; fi
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-$OWNER}" -c user.email="${GIT_AUTHOR_EMAIL:-$OWNER@users.noreply.github.com}" \
  commit -q -m "Daily Stop" || true

# 2. Create the public repo and push (skip creation if it already exists)
if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
  git push -u origin main
else
  gh repo create "$REPO" --public --source=. --remote=origin --push \
    --description "My daily AI / LLM / tech news page"
fi

# 3. Turn on GitHub Pages, published by GitHub Actions
if gh api "repos/$OWNER/$REPO/pages" >/dev/null 2>&1; then
  gh api -X PUT "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null
else
  gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null
fi
echo "GitHub Pages enabled."

# 4. Run the workflow once to publish the first feed
sleep 5
gh workflow run refresh.yml --repo "$OWNER/$REPO" --ref main
echo
echo "Publishing now (about 1–2 minutes). Follow along with:"
echo "  gh run watch --repo $OWNER/$REPO"
echo
echo "Your page: https://$OWNER.github.io/$REPO/"
