#!/usr/bin/env bash

MY_CHANGES=0

# GitHub Action runner
if [ -v GITHUB_RUN_ID ]; then
	echo "» Set git username and email"
	git config user.name "github-actions[bot]"
	git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
fi

# Roles
MY_ROLES_TXT="roles.txt"
if ! git diff --exit-code "$MY_ROLES_TXT"; then
	echo "'$MY_ROLES_TXT' changed!"
	git add "$MY_ROLES_TXT"
	((MY_CHANGES++));
fi

# Commit and push
if [ "$MY_CHANGES" -ge 1 ]; then
	echo "Commit and push to repo..."
	git commit -m "IAM changes" || exit 9
	git push || exit 9
fi

echo "DONE"