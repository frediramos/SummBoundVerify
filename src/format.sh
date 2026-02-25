#!/bin/bash

# Resolve this script's directory
DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" \
  && pwd
)"

# Default settings
AGGRESSIVE=false
VERBOSE=false

# Parse CLI options
while getopts "avh" opt; do
  case "$opt" in
    a) AGGRESSIVE=true ;;
    v) VERBOSE=true ;;
    h)
       echo "Usage: $0 [-a] [-v] [-h]"
       echo "  -a    Apply aggressive autopep8 fixes"
       echo "  -v    Enable verbose output"
       echo "  -h    Show this help message"
       exit 0
       ;;
    *) 
       echo "Invalid option. Use -h for help."
       exit 1
       ;;
  esac
done

# Build command
CMD="autopep8 -i -r"

if [ "$AGGRESSIVE" = true ]; then
  CMD="$CMD --aggressive"
fi

if [ "$VERBOSE" = true ]; then
  CMD="$CMD --verbose"
fi

# Run autopep8
$CMD "."
