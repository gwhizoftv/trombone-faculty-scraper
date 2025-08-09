#!/opt/homebrew/bin/bash
set -euo pipefail
#set -x  # debug tracing

# Determine REPO_ROOT: argument or auto-detect
if [ -n "${1:-}" ]; then
  ARG_REPO_ROOT_PATH="$1"
  if [[ "$ARG_REPO_ROOT_PATH" == /* ]]; then
    REPO_ROOT="$ARG_REPO_ROOT_PATH"
  else
    REPO_ROOT="$(cd "$ARG_REPO_ROOT_PATH" && pwd)"
  fi
else
  SCRIPT_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  REPO_ROOT="$(cd "$SCRIPT_SELF_DIR/.." && pwd)"
fi

AGENT_COUNT=2
PROJECT_NAME="$(basename "$REPO_ROOT")"
PARENT_DIR="$(dirname "$REPO_ROOT")"

if [ ! -d "$REPO_ROOT" ]; then
  echo "Error: REPO_ROOT '$REPO_ROOT' is not a valid directory." >&2
  exit 1
fi

echo "🚀 Launching $AGENT_COUNT Gemini agent tabs in isolated repos"
echo "   Original repo: $REPO_ROOT"
echo "   Parent directory: $PARENT_DIR"

# Validate that isolated repos exist
echo "🔍 Checking for isolated agent repos..."
for i in $(seq 1 $AGENT_COUNT); do
  AGENT_REPO_DIR="$PARENT_DIR/${PROJECT_NAME}-gemini$i"
  if [ ! -d "$AGENT_REPO_DIR" ]; then
    echo "❌ Error: Isolated repo not found: $AGENT_REPO_DIR" >&2
    echo "   Please run the isolated setup script first:" >&2
    echo "   ./scripts/gemini_agent_setup_isolated.sh" >&2
    exit 1
  fi
  echo "   ✅ Agent $i repo found: $AGENT_REPO_DIR"
done

echo "Building AppleScript commands..."

for i in $(seq 1 $AGENT_COUNT); do
  PROFILE_NAME="Gemini $i"
  AGENT_REPO_DIR="$PARENT_DIR/${PROJECT_NAME}-gemini$i"
  
  # Updated command to run in the isolated agent's repo
  CMD_TO_RUN_IN_AGENT_SHELL="cd '$AGENT_REPO_DIR' && ./start-gemini.sh"

  echo "   🖥️  Launching Agent $i in: $AGENT_REPO_DIR"
  
  osascript -e "tell application \"Terminal\" to activate" \
            -e "tell application \"Terminal\" to set newWindow to do script \"\"" \
            -e "tell application \"Terminal\" to set current settings of newWindow to settings set \"$PROFILE_NAME\"" \
            -e "tell application \"Terminal\" to do script \"$CMD_TO_RUN_IN_AGENT_SHELL\" in newWindow"
done

echo "✅ All agent launch commands sent to Terminal."
echo "📁 Each agent is now running in their isolated repository:"
for i in $(seq 1 $AGENT_COUNT); do
  AGENT_REPO_DIR="$PARENT_DIR/${PROJECT_NAME}-gemini$i"
  echo "   Agent $i: $AGENT_REPO_DIR"
done