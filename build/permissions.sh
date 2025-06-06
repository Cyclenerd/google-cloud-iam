#!/usr/bin/env bash

MY_ROLES_JSON="roles.json"
MY_ROLES_TXT="roles.txt"
MY_CSV="permissions.csv"

echo "Get permissions... Please wait..."

printf '%s;%s\n' "name" "permissions" > "$MY_CSV" || exit 9

jq '.[].name' "$MY_ROLES_JSON" | sort -u > "$MY_ROLES_TXT" || exit 9

MY_COUNT=1
while read -r MY_NAME; do
	MY_NAME=${MY_NAME//\"/}
	# Skip basic roles
	if [[ "$MY_NAME" = "roles/reader" || "$MY_NAME" = "roles/writer" || "$MY_NAME" = "roles/admin" ]]; then
		continue
	fi
	# Skip legacy basic roles originally known as primitive roles
	if [[ "$MY_NAME" = "roles/owner" || "$MY_NAME" = "roles/editor" || "$MY_NAME" = "roles/viewer" ]]; then
		continue
	fi
	echo "[$MY_COUNT] $MY_NAME"
	MY_PERMISSIONS=$(gcloud iam roles describe "$MY_NAME" --quiet \
		--format="csv[no-heading,separator=';'](includedPermissions)")
	MY_PERMISSIONS=${MY_PERMISSIONS//;/,}
	printf '%s;%s\n' "$MY_NAME" "$MY_PERMISSIONS" >> "$MY_CSV" || exit 9
	((MY_COUNT++))
done <"$MY_ROLES_TXT"

echo "Quick test"
grep "roles/compute.admin" "$MY_CSV" || exit 9
grep "roles/bigquery.admin" "$MY_CSV" || exit 9
grep "roles/billing.admin" "$MY_CSV" || exit 9

echo "DONE"
