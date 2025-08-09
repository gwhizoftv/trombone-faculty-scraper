#!/opt/homebrew/bin/bash
set -euo pipefail
# Make sure NVM_DIR is set, if not, default to /Users/MGW/.nvm
export NVM_DIR="/Users/MGW/.nvm"

if [ -s "/Users/MGW/.nvm/nvm.sh" ]; then
  # shellcheck source=/dev/null
  . "/Users/MGW/.nvm/nvm.sh"
else
  echo "Error: NVM script not found at /Users/MGW/.nvm/nvm.sh" >&2
  echo "Please check your NVM installation and NVM_DIR." >&2
  exit 1
fi
cd '/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1'
# Use appropriate Node version based on project
if [[ -f .nvmrc ]]; then
  nvm use
else
  nvm use 22
fi
sleep 2
git stash clear
claude --version
exec claude code --verbose
