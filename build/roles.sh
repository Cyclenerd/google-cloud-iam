#!/usr/bin/env bash

echo "Get role permission filter... Please wait..."
# Source: https://docs.cloud.google.com/iam/docs/roles-permissions
curl -O "https://docs.cloud.google.com/iam/json/role-permission-filter.json"

echo "Get roles... Please wait..."
gcloud iam roles list --quiet \
	--sort-by="name" \
	--format="json" > "roles.json" || exit 9

echo "DONE"
