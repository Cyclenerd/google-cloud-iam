#!/usr/bin/env bash

echo "Get role permission filter... Please wait..."
curl -O "https://cloud.google.com/iam/json/role-permission-filter.json"

echo "Get roles... Please wait..."
gcloud iam roles list --quiet \
	--sort-by="name" \
	--format="json" > "roles.json" || exit 9

echo "DONE"