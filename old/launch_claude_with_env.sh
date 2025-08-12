#!/bin/bash
# Launch Claude Desktop with proper environment

# Load nvm and set Node version
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 22.14.0

# Set proper PATH
export PATH="/Users/MGW/.nvm/versions/node/v22.14.0/bin:$PATH"

# Launch Claude Desktop
open /Applications/Claude.app

echo "Claude Desktop launched with Node v22.14.0 environment"