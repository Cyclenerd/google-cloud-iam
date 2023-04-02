#!/usr/bin/env bash

echo "Get roles... Please wait..."

gcloud iam roles list --quiet \
	--sort-by="name" \
	--format="json" > "roles.json" || exit 9

echo "DONE"