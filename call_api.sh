#!/bin/bash

# Default values
IDENTIFIER=${1:-"example_purchaser_123"}
TEXT=${2:-"Write a story about a robot learning to paint"}
OUTPUT_FILE=${3:-"response.json"}
TOKEN=${4:-"iofsnaiojdoiewqajdriknjonasfoinasd"}
STATUS_HOST=${5:-"0.0.0.0:8000"}

# Call first API and store response
RESPONSE=$(curl -s -X 'POST' \
  'https://masumi.vespr.xyz/start_job' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
  \"identifier_from_purchaser\": \"$IDENTIFIER\",
  \"input_data\": {
    \"text\": \"$TEXT\"
  }
}")

# Save response to file
echo "$RESPONSE" > "$OUTPUT_FILE"
echo "First API response stored in $OUTPUT_FILE"

# Extract values from first response
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
BLOCKCHAIN_ID=$(echo "$RESPONSE" | jq -r '.blockchainIdentifier')
SUBMIT_TIME=$(echo "$RESPONSE" | jq -r '.submitResultTime')
UNLOCK_TIME=$(echo "$RESPONSE" | jq -r '.unlockTime')
DISPUTE_TIME=$(echo "$RESPONSE" | jq -r '.externalDisputeUnlockTime')
AGENT_ID=$(echo "$RESPONSE" | jq -r '.agentIdentifier')
SELLER_VKEY=$(echo "$RESPONSE" | jq -r '.sellerVkey')
INPUT_HASH=$(echo "$RESPONSE" | jq -r '.input_hash')
AMOUNTS=$(echo "$RESPONSE" | jq -c '.amounts')

# Call second API
echo "Calling payment API..."
PAYMENT_RESPONSE=$(curl -s -X 'POST' \
  'https://payment.masumi.network/api/v1/purchase/' \
  -H 'accept: application/json' \
  -H "token: $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"status\": \"success\",
    \"network\": \"Preprod\",
    \"paymentType\": \"Web3CardanoV1\",
    \"job_id\": \"$JOB_ID\",
    \"blockchainIdentifier\": \"$BLOCKCHAIN_ID\",
    \"submitResultTime\": \"$SUBMIT_TIME\",
    \"unlockTime\": \"$UNLOCK_TIME\",
    \"externalDisputeUnlockTime\": \"$DISPUTE_TIME\",
    \"agentIdentifier\": \"$AGENT_ID\",
    \"sellerVkey\": \"$SELLER_VKEY\",
    \"identifierFromPurchaser\": \"$IDENTIFIER\",
    \"amounts\": $AMOUNTS,
    \"inputHash\": \"$INPUT_HASH\"
}")

# Save payment response
echo "$PAYMENT_RESPONSE" > "payment_$OUTPUT_FILE"
echo "Payment API response stored in payment_$OUTPUT_FILE"


# wait for 6 minutes
sleep 360

# Call status API
echo "Checking job status..."
STATUS_RESPONSE=$(curl -s -X 'GET' \
  "http://$STATUS_HOST/status?job_id=$JOB_ID" \
  -H 'accept: application/json')

# Save status response
echo "$STATUS_RESPONSE" > "status_$OUTPUT_FILE"
echo "Status API response stored in status_$OUTPUT_FILE"



