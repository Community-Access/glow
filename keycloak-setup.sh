#!/bin/bash
# keycloak-setup.sh: Automate Keycloak SSO setup for GLOW (Google + GitHub)
# Usage: bash keycloak-setup.sh

# --- CONFIG ---
KEYCLOAK_URL="https://glow.bits-acb.org/auth"
REALM="glow"
ADMIN_USER="admin"
# Prompt for admin password securely
read -sp "Enter Keycloak admin password: " ADMIN_PWD; echo

# --- USERS & ROLES ---
# Users: email, username, roles
USERS=(
  "jeff.bishop@bits-acb.org::admin"
  "jeff.bishop@bitsusers.org::user"
  "jeffbis@arizona.edu:accesswatch:admin"
  "jeff.bishop@outlook.com:access-watch-student:user"
)

# --- FUNCTIONS ---
get_token() {
  curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -d "username=$ADMIN_USER" -d "password=$ADMIN_PWD" \
    -d 'grant_type=password' -d 'client_id=admin-cli' \
    | jq -r .access_token
}

create_user() {
  local email="$1"; local username="$2"; local role="$3"; local token="$4"
  local user_json="{\"email\":\"$email\",\"username\":\"$username\",\"enabled\":true,\"emailVerified\":true}"
  curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "$user_json"
  # Get user ID
  local uid=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users?email=$email" \
    -H "Authorization: Bearer $token" | jq -r '.[0].id')
  # Assign role
  local role_id=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/roles/$role" \
    -H "Authorization: Bearer $token" | jq -r '.id')
  curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$uid/role-mappings/realm" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "[{\"id\":\"$role_id\",\"name\":\"$role\"}]"
}

# --- MAIN ---
TOKEN=$(get_token)

# Create roles if not exist
declare -a ROLES=("admin" "user")
for role in "${ROLES[@]}"; do
  curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"name\":\"$role\"}" >/dev/null
done

# Create users and assign roles
for entry in "${USERS[@]}"; do
  IFS=":" read -r email username role <<< "$entry"
  [ -z "$username" ] && username="$email"
  create_user "$email" "$username" "$role" "$TOKEN"
done

echo "Users and roles created."

# --- GOOGLE IDP SETUP ---
echo "\n--- Google IdP ---"
echo "In Keycloak admin UI, add Google as an Identity Provider:"
echo "- Provider: Google"
echo "- Client ID/Secret: (from Google Cloud Console)"
echo "- Redirect URI: $KEYCLOAK_URL/realms/$REALM/broker/google/endpoint"
echo "- Save and enable."

# --- GITHUB IDP SETUP ---
echo "\n--- GitHub IdP ---"
echo "In Keycloak admin UI, add GitHub as an Identity Provider:"
echo "- Provider: GitHub"
echo "- Client ID/Secret: (from GitHub OAuth app)"
echo "- Redirect URI: $KEYCLOAK_URL/realms/$REALM/broker/github/endpoint"
echo "- Save and enable."

echo "\nDone. Now configure OIDC client for GLOW and test SSO."
