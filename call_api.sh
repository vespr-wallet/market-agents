#!/bin/bash

# Default values
IDENTIFIER=${1:-"123123123123123"}
TEXT=${2:-"Analyze these tweets about $NMKR cryptocurrency and provide a detailed sentiment analysis. Identify key complaints, potential red flags, and give your assessment on whether this appears to be a legitimate project facing challenges or potentially fraudulent."}
OUTPUT_FILE=${3:-"response.json"}
TOKEN=${4:-"iofsnaiojdoiewqajdriknjonasfoinasd"}
STATUS_HOST=${5:-"0.0.0.0:8000"}

# Echo the start job curl command
echo "Executing start job curl command:"
echo "curl -X 'POST' 'http://localhost:8000/start_job' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{\"identifier_from_purchaser\": \"$IDENTIFIER\", \"input_data\": {\"text\": \"$TEXT\"}}'"

# Call first API and store response
RESPONSE=$(curl -s -X 'POST' \
  'http://localhost:8000/start_job' \
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
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')re
BLOCKCHAIN_ID=$(echo "$RESPONSE" | jq -r '.blockchainIdentifier')
SUBMIT_TIME=$(echo "$RESPONSE" | jq -r '.submitResultTime')
UNLOCK_TIME=$(echo "$RESPONSE" | jq -r '.unlockTime')
DISPUTE_TIME=$(echo "$RESPONSE" | jq -r '.externalDisputeUnlockTime')
AGENT_ID=$(echo "$RESPONSE" | jq -r '.agentIdentifier')
SELLER_VKEY=$(echo "$RESPONSE" | jq -r '.sellerVkey')
INPUT_HASH=$(echo "$RESPONSE" | jq -r '.input_hash')
AMOUNTS=$(echo "$RESPONSE" | jq -c '.amounts')

# Echo the payment API curl command
echo "Executing payment API curl command:"
echo "curl -X 'POST' 'https://payment.masumi.network/api/v1/purchase/' -H 'accept: application/json' -H 'token: $TOKEN' -H 'Content-Type: application/json' -d '{\"status\": \"success\", \"network\": \"Preprod\", \"paymentType\": \"Web3CardanoV1\", \"job_id\": \"$JOB_ID\", \"blockchainIdentifier\": \"$BLOCKCHAIN_ID\", \"submitResultTime\": \"$SUBMIT_TIME\", \"unlockTime\": \"$UNLOCK_TIME\", \"externalDisputeUnlockTime\": \"$DISPUTE_TIME\", \"agentIdentifier\": \"$AGENT_ID\", \"sellerVkey\": \"$SELLER_VKEY\", \"identifierFromPurchaser\": \"$IDENTIFIER\", \"amounts\": $AMOUNTS, \"inputHash\": \"$INPUT_HASH\"}'"

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


# Countdown for 6 minutes (360 seconds)
echo "Waiting for job to complete. Starting 6 minute countdown..."
TOTAL_SECONDS=360
for ((i=TOTAL_SECONDS; i>=0; i--)); do
    # Calculate minutes and seconds for display
    minutes=$((i / 60))
    seconds=$((i % 60))
    
    # Use carriage return to overwrite the same line
    printf "\rTime remaining: %02d:%02d" $minutes $seconds
    
    # Don't sleep after the last iteration
    if [ $i -gt 0 ]; then
        sleep 1
    fi
done
echo -e "\nCountdown complete!"

# Echo the status API curl command
echo "Executing status API curl command:"
echo "curl -X 'GET' 'http://localhost:8000/status?job_id=$JOB_ID' -H 'accept: application/json'"

# Call status API
echo "Checking job status..."
STATUS_RESPONSE=$(curl -s -X 'GET' \
  "http://localhost:8000/status?job_id=$JOB_ID" \
  -H 'accept: application/json')

# Save status response
echo "$STATUS_RESPONSE" > "status_$OUTPUT_FILE"
echo "Status API response stored in status_$OUTPUT_FILE"



