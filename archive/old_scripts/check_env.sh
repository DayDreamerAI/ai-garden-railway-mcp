#!/bin/bash

# Load environment from root .env if it exists
if [[ -f "../../../../.env" ]]; then
  set -a
  source ../../../../.env
  set +a
fi

echo "Checking environment variables for Railway deployment:"
echo ""

check_var() {
  local var_name=$1
  local var_value="${!var_name}"
  
  if [[ -n "$var_value" ]]; then
    # Mask sensitive values
    local masked_value
    if [[ ${#var_value} -gt 8 ]]; then
      masked_value="${var_value:0:4}...${var_value: -4}"
    else
      masked_value="***"
    fi
    echo "✅ $var_name: $masked_value"
  else
    echo "❌ $var_name: NOT SET"
  fi
}

check_var "RAILWAY_TOKEN"
check_var "NEO4J_URI"
check_var "NEO4J_PASSWORD"
check_var "RAILWAY_BEARER_TOKEN"

echo ""
echo "Note: Script will use RAILWAY_TOKEN from .env for deployment"
