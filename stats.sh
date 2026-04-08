#!/bin/bash
#trying to output json data

# Path to where your dashboard looks for data
OUTPUT_PATH="/var/www/html/cluster-stats.json"

# Get Node data and format it into a clean JSON object using jq
nodes_json=$(kubectl get nodes -o json | jq -c '[.items[] | {name: .metadata.name, status: .status.conditions[-1].type, cpu: .status.capacity.cpu, mem: .status.capacity.memory}]')

# Get Pod stats
pod_count=$(kubectl get pods -A --no-headers | wc -l)

# Combine into one final JSON file
echo "{\"nodes\": $nodes_json, \"total_pods\": $pod_count, \"last_updated\": \"$(date)\"}" > $OUTPUT_PATH
