#!/opt/homebrew/bin/bash
# Dry-run enabled via -n or --dry-run: commands will be echoed instead of executed
set -euo pipefail
set -x

# claude_agent_setup_isolated.sh - Bootstraps a multi-agent Claude Code environment with isolated repos.
# Usage: ./scripts/claude_agent_setup_isolated.sh [-n|--dry-run] [remote_name] [shared_branch]

AGENT_COUNT=1
TEAM_SIZE=$AGENT_COUNT
REMOTE_NAME=${1:-origin}
SHARED_BRANCH=${2:-main}
TREE_SCRIPT="directory_tree.sh"

# Parse dry-run flag
dry_run=false
if [[ "${1:-}" == "-n" || "${1:-}" == "--dry-run" ]]; then
  dry_run=true
  shift
fi

# Wrapper for command execution or echo
run_cmd() {
  if [[ "$dry_run" == true ]]; then
    printf "DRY-RUN: %s\n" "$*"
  else
    eval "$*"
  fi
}

# Helper function to check if a Git operation is in progress
is_git_operation_in_progress() {
  local repo_path="$1"
  local git_dir="$repo_path/.git"

  if [[ ! -d "$git_dir" ]]; then
    return 1 # Not a git repository, or .git directory not found
  fi

  # Check for common Git operation markers
  if [[ -f "$git_dir/MERGE_HEAD" ]]; then
    echo "    (Git merge in progress)"
    return 0 # True, a merge is active
  fi
  if [[ -d "$git_dir/rebase-merge" || -f "$git_dir/rebase-apply/next" || -f "$git_dir/REBASE_HEAD" ]]; then
    echo "    (Git rebase in progress)"
    return 0 # True, a rebase is active
  fi
  if [[ -f "$git_dir/CHERRY_PICK_HEAD" ]]; then
    echo "    (Git cherry-pick in progress)"
    return 0 # True, a cherry-pick is active
  fi
  if [[ -f "$git_dir/BISECT_START" ]]; then
    echo "    (Git bisect in progress)"
    return 0 # True, a bisect is active
  fi
  return 1 # False, no active operation found
}


# Framework detection function
detect_project_type() {
  local project_dir="$1"
  local project_type="unknown"
  
  if [[ -f "$project_dir/package.json" ]]; then
    if grep -qE '"react":|"react-native":' "$project_dir/package.json" 2>/dev/null; then
      if grep -q '"react-native":' "$project_dir/package.json" 2>/dev/null; then
        project_type="react-native"
      else
        project_type="react"
      fi
    elif grep -q '"typescript":' "$project_dir/package.json" 2>/dev/null || [[ -f "$project_dir/tsconfig.json" ]]; then
      project_type="typescript"
    else
      project_type="javascript"
    fi
  elif [[ -f "$project_dir/pubspec.yaml" ]]; then
    if grep -q 'flutter:' "$project_dir/pubspec.yaml" 2>/dev/null; then
      project_type="flutter"
    else
      project_type="dart"
    fi
  elif [[ -f "$project_dir/Cargo.toml" ]]; then
    project_type="rust"
  elif [[ -f "$project_dir/go.mod" ]]; then
    project_type="go"
  elif [[ -f "$project_dir/requirements.txt" ]] || [[ -f "$project_dir/setup.py" ]] || [[ -f "$project_dir/pyproject.toml" ]]; then
    project_type="python"
  fi
  
  echo "$project_type"
}

# Get lint/test commands based on project type
get_lint_command() {
  local project_type="$1"
  case "$project_type" in
    javascript|typescript|react|react-native)
      echo "npm run lint"
      ;;
    flutter|dart)
      echo "flutter analyze"
      ;;
    rust)
      echo "cargo clippy"
      ;;
    go)
      echo "go vet ./..."
      ;;
    python)
      echo "flake8 . || pylint **/*.py"
      ;;
    *)
      echo "echo 'No lint command configured for this project type'"
      ;;
  esac
}

get_test_command() {
  local project_type="$1"
  case "$project_type" in
    javascript|typescript|react|react-native)
      echo "npm test"
      ;;
    flutter|dart)
      echo "flutter test"
      ;;
    rust)
      echo "cargo test"
      ;;
    go)
      echo "go test ./..."
      ;;
    python)
      echo "pytest || python -m pytest"
      ;;
    *)
      echo "echo 'No test command configured for this project type'"
      ;;
  esac
}

get_typecheck_command() {
  local project_type="$1"
  case "$project_type" in
    javascript|react|react-native)
      echo "npx tsc --noEmit"
      ;;
    typescript)
      echo "npx tsc --noEmit"
      ;;
    flutter|dart)
      echo "dart analyze"
      ;;
    python)
      echo "mypy ."
      ;;
    *)
      echo "echo 'No typecheck command for this project type'"
      ;;
  esac
}

# 1) Detect Git repo root and project name
echo "Detecting Git repo root..."
CURRENT_REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_PROJECT_NAME="$(basename "$CURRENT_REPO_ROOT")"
PARENT_DIR="$(dirname "$CURRENT_REPO_ROOT")"

ORIGINAL_PROJECT_NAME="$CURRENT_PROJECT_NAME"
ORIGINAL_REPO_ROOT="$CURRENT_REPO_ROOT"

if [[ "$CURRENT_PROJECT_NAME" =~ ^(.*)-claude[0-9]+$ ]]; then
  ORIGINAL_PROJECT_NAME="${BASH_REMATCH[1]}"
  ORIGINAL_REPO_ROOT="$PARENT_DIR/$ORIGINAL_PROJECT_NAME"
  echo "Detected script running from an agent clone: '$CURRENT_PROJECT_NAME'."
  echo "Assuming original project name is: '$ORIGINAL_PROJECT_NAME' located at '$ORIGINAL_REPO_ROOT'."

  if [[ ! -d "$ORIGINAL_REPO_ROOT" ]]; then
    echo "ERROR: Assumed original repository '$ORIGINAL_REPO_ROOT' not found!" >&2
    echo "Please ensure '$ORIGINAL_REPO_ROOT' exists and is a valid git repository." >&2
    echo "It's highly recommended to run this script from the root of your original project (e.g., 'OneUp')," >&2
    echo "or ensure the original project is a sibling to the agent clones." >&2
    exit 1
  fi
fi

echo "Getting original remote URL from $ORIGINAL_REPO_ROOT..."
ORIGINAL_REMOTE_URL=$(cd "$ORIGINAL_REPO_ROOT" && git config --get remote.origin.url)
if [ -z "$ORIGINAL_REMOTE_URL" ]; then
  echo "WARNING: Could not determine remote.origin.url for '$ORIGINAL_REPO_ROOT'." >&2
  echo "Please ensure '$ORIGINAL_REPO_ROOT' has a 'origin' remote configured (e.g., 'git remote add origin <your-github-url>')." >&2
  echo "Cloned repositories' origins might be incorrect (pointing to local path)." >&2
else
  echo "Original remote URL detected: $ORIGINAL_REMOTE_URL"
  if ! [[ "$ORIGINAL_REMOTE_URL" =~ ^(git@|https://) ]]; then
    echo "WARNING: Unusual remote URL format detected: $ORIGINAL_REMOTE_URL" >&2
    echo "This might indicate a local path, or a less common remote protocol." >&2
  fi
fi

# 1.a) Ensure we clone fresh copies
for i in $(seq 1 $AGENT_COUNT); do
  TARGET="$PARENT_DIR/${ORIGINAL_PROJECT_NAME}-claude$i"
  if [[ -d "$TARGET" ]]; then
    echo "Using existing clone: $TARGET"
  else
    echo "Cloning for Agent $i: $TARGET"
    run_cmd "git clone '$ORIGINAL_REPO_ROOT' '$TARGET'"
    if [[ -n "$ORIGINAL_REMOTE_URL" ]]; then
      echo "  • Setting origin remote in $TARGET to $ORIGINAL_REMOTE_URL"
      run_cmd "cd '$TARGET' && git remote set-url origin '$ORIGINAL_REMOTE_URL'"
    fi
  fi
done

# 1.b) Create or update .gitignore in each clone
for i in $(seq 1 "$AGENT_COUNT"); do
  CLONE="${PARENT_DIR}/${ORIGINAL_PROJECT_NAME}-claude$i"
  GITIGNORE="$CLONE/.gitignore"

  declare -a DESIRED_GITIGNORE_TEMPLATE=(
    "" 
    "# Claude per-agent files"
    ".claude/"
    ".claude*/"
    "start.sh"
    ".githooks/"
    "CLAUDE.md"
    "CLAUDE.local.md"
    ""
    "# Start scripts (agent-specific)"
    "directory_tree.md"
    "# ctags files"
    "tags"
  )

  declare -a DESIRED_GITIGNORE_PATTERNS=()
  for line in "${DESIRED_GITIGNORE_TEMPLATE[@]}"; do
    trimmed_line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -n "$trimmed_line" && ! "$trimmed_line" =~ ^\# ]]; then
      DESIRED_GITIGNORE_PATTERNS+=("$trimmed_line")
    fi
  done
  readarray -t DESIRED_GITIGNORE_PATTERNS < <(printf '%s\n' "${DESIRED_GITIGNORE_PATTERNS[@]}" | sort -u)


  GITIGNORE_WAS_MODIFIED=false
  echo "Processing .gitignore for $CLONE"

  if [[ ! -f "$GITIGNORE" ]]; then
    echo "  • Creating .gitignore in $CLONE"
    for line in "${DESIRED_GITIGNORE_TEMPLATE[@]}"; do
      run_cmd "printf '%s\n' \"$line\" >> \"$GITIGNORE\""
    done
    GITIGNORE_WAS_MODIFIED=true
  else
    echo "  • Updating .gitignore in $CLONE"

    declare -a CURRENT_GITIGNORE_PATTERNS=()
    while IFS= read -r line; do
      trimmed_line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      if [[ -n "$trimmed_line" && ! "$trimmed_line" =~ ^\# ]]; then
        CURRENT_GITIGNORE_PATTERNS+=("$trimmed_line")
      fi
    done < "$GITIGNORE"
    readarray -t CURRENT_GITIGNORE_PATTERNS < <(printf '%s\n' "${CURRENT_GITIGNORE_PATTERNS[@]}" | sort -u)

    desired_patterns_file=$(mktemp)
    current_patterns_file=$(mktemp)
    printf '%s\n' "${DESIRED_GITIGNORE_PATTERNS[@]}" > "$desired_patterns_file"
    printf '%s\n' "${CURRENT_GITIGNORE_PATTERNS[@]}" > "$current_patterns_file"

    declare -a MISSING_PATTERNS=()
    while IFS= read -r line; do
      MISSING_PATTERNS+=("$line")
    done < <(comm -13 "$current_patterns_file" "$desired_patterns_file")

    rm "$desired_patterns_file" "$current_patterns_file"

    if [[ ${#MISSING_PATTERNS[@]} -gt 0 ]]; then
      echo "  • Appending missing rules to $GITIGNORE:"
      if [[ -s "$GITIGNORE" ]]; then
        last_char=$(tail -c 1 "$GITIGNORE")
        if [[ "$last_char" != $'\n' ]]; then
          run_cmd "printf '\n' >> \"$GITIGNORE\""
        fi
      fi
      run_cmd "printf '\n' >> \"$GITIGNORE\""
      run_cmd "printf '# Added by setup script\n' >> \"$GITIGNORE\""
      for line in "${MISSING_PATTERNS[@]}"; do
        echo "    - $line"
        run_cmd "printf '%s\n' \"$line\" >> \"$GITIGNORE\""
      done
      GITIGNORE_WAS_MODIFIED=true
    else
      echo "  • All required .gitignore patterns already present in $GITIGNORE."
    fi
  fi

  if [[ "$GITIGNORE_WAS_MODIFIED" == true ]]; then
    echo "  • .gitignore was modified on disk."
    if is_git_operation_in_progress "$CLONE"; then
      echo "  ⚠ Skipping commit: Git operation in progress in $CLONE"
      echo "    Please resolve the Git operation (e.g., merge/rebase) and then manually commit the .gitignore file:"
      echo "    (cd '$CLONE' && git add .gitignore && git commit -m 'feat(setup): Add agent-specific .gitignore rules')"
    else
      if ( cd "$CLONE" && git diff --quiet --exit-code .gitignore &>/dev/null && git diff --cached --quiet --exit-code .gitignore &>/dev/null ); then
          echo "  • .gitignore file is already clean (no pending changes to commit in Git)."
      else
        run_cmd "cd '$CLONE' && git add .gitignore && git commit -m 'feat(setup): Add agent-specific .gitignore rules' --no-verify || true"
        echo "  • .gitignore commit attempted."
        echo "    (Note: '|| true' on commit command prevents script exit if 'nothing to commit' or other benign Git issues.)"
      fi
    fi
  else
    echo "  • No changes needed in $CLONE/.gitignore"
  fi
  echo "---"
done

# 2) In each clone, set up config, memory, and scripts
for i in $(seq 1 $AGENT_COUNT); do
  CLONE_DIR="$PARENT_DIR/${ORIGINAL_PROJECT_NAME}-claude$i"
  echo "Setting up Agent $i in $CLONE_DIR on branch $SHARED_BRANCH"

  run_cmd "cd '$CLONE_DIR'"

  # Install MCP servers. If we install multiple times, the || true handles it
  echo "   • Installing MCP servers in '$CLONE_DIR' ..."
  run_cmd "claude mcp add --transport sse context7 https://mcp.context7.com/sse || true"
  run_cmd "claude mcp add filesystem -s project -- npx -y @modelcontextprotocol/server-filesystem '$CLONE_DIR' || true"
  echo "   • Ensuring a clean working directory in '$CLONE_DIR' for sync..."
  run_cmd "git reset --hard HEAD || true"
  run_cmd "git clean -fdx || true"

  echo "   • Clearing existing stashes..."
  run_cmd "git stash clear || true"

  echo "   • Stashing any current local changes (if any)..."
  run_cmd "git diff-index --quiet HEAD -- || git stash push -u -m 'autostash for setup sync' || true"

  echo "   • Checking out '$SHARED_BRANCH'..."
  run_cmd "git checkout '$SHARED_BRANCH'"

  echo "   • Fetching latest from '$REMOTE_NAME/$SHARED_BRANCH'..."
  run_cmd "git fetch '$REMOTE_NAME' '$SHARED_BRANCH'"

  echo "   • Force-syncing local '$SHARED_BRANCH' with '$REMOTE_NAME/$SHARED_BRANCH'..."
  run_cmd "git reset --hard '$REMOTE_NAME/$SHARED_BRANCH'"

  echo "   • Reapplying stashed changes (if any)..."
  if ! run_cmd "git stash pop --index || true"; then
      echo "  ⛔ Stash pop resulted in conflicts in '$CLONE_DIR'." >&2
      echo "     Please resolve these conflicts manually and then commit. Use 'git status' to see conflicted files." >&2
      echo "     The setup script will continue for other agents, but this agent will need attention." >&2
  fi

  echo "   • Repository synced with '$SHARED_BRANCH' (or left with stash conflicts)."
  
  PROJECT_TYPE=$(detect_project_type "$CLONE_DIR")
  echo "   • Detected project type: $PROJECT_TYPE"
  
  if [[ "$PROJECT_TYPE" =~ ^(javascript|typescript|react|react-native)$ ]]; then
    echo "   • Cleaning up old dependencies and lock files..."
    run_cmd "cd '$CLONE_DIR' && rm -rf node_modules package-lock.json || true"

    if [[ -f "$CLONE_DIR/package.json" ]] && ! grep -q '"typescript":' "$CLONE_DIR/package.json" 2>/dev/null; then
      echo "   • Installing TypeScript for type checking..."
      run_cmd "cd '$CLONE_DIR' && npm install --save-dev typescript @types/node || true"
    fi
    echo "   • Installing project dependencies from package.json..."
    run_cmd "cd '$CLONE_DIR' && npm install || true"
  fi
  
  LINT_CMD=$(get_lint_command "$PROJECT_TYPE")
  TEST_CMD=$(get_test_command "$PROJECT_TYPE")
  TYPECHECK_CMD=$(get_typecheck_command "$PROJECT_TYPE")

  run_cmd "mkdir -p '$CLONE_DIR'"
  run_cmd "mkdir -p '$CLONE_DIR'/.claude"
  run_cmd "mkdir -p '$CLONE_DIR/.claude/tmp'"
 run_cmd "cat > '$CLONE_DIR/CLAUDE.md' <<EOF
# Project memory for Claude Agent $i
  ## CRITICAL: Which agent are you? ($TEAM_SIZE agents active = confusion)
  
  You are Claude $i here. The user is running $TEAM_SIZE different agents simultaneously 
  and gets confused about who said what. Last week, Claude 3 accidentally overwrote 
  Claude 1's work because the user thought they were talking to Claude 2.
  
  Solution: Start responses with \"Claude $i here\" when it matters (first response, 
  after errors, when confirming actions). Not robotic - just clear.
  
  Working in: $CLONE_DIR  
  
  ## BEFORE STARTING ANY TASK - MANDATORY CODE UPDATE
  ⚠️  ALWAYS start with these commands for ANY new request:
  - git checkout $SHARED_BRANCH
  - git pull origin $SHARED_BRANCH
  
  ## TRIGGER WORDS that REQUIRE immediate code update:
  - \"bug\" / \"issue\" / \"problem\" / \"error\" / \"broken\"
  - \"analyze\" / \"investigate\" / \"look at\" / \"check\"
  - \"fix\" / \"update\" / \"modify\" / \"change\" / \"add\"
  - \"we have\" / \"there is\" / \"I see\" / \"found\"
  - ANY request about existing code
  
  ## WHY: Other agents may have made changes since your last pull
  
  ## CORRECT RESPONSE PATTERN:
  User: \"We have a bug in xyz, analyze the problem...\"
  Claude $i: \"Let me first get the latest code from other agents:
  \\\`\\\`\\\`bash
  git checkout $SHARED_BRANCH
  git pull origin $SHARED_BRANCH
  \\\`\\\`\\\`
  Now I'll analyze the xyz problem...\"
  
  ## BEFORE ANY CODE EDIT - MANDATORY CHECK
  When user asks for ANY code change, your FIRST response MUST be:
  \"Claude $i: Starting git workflow for [brief description]\"
  Then show the git commands you'll run.
  
  ## DANGER WORDS that trigger git workflow:
  - \"make that change\"
  - \"ok\" (after discussing code)
  - \"fix\"
  - \"update\" 
  - \"add\"
  - \"implement\"
  
  ## MANDATORY: PR-Based Workflow (CI/CD Integration)
  ⚠️  ALL changes must go through Pull Requests for Runway CI/CD integration.
  ⚠️  Direct merges to $SHARED_BRANCH are FORBIDDEN.
  
 ## The safe git workflow pattern (memorize this flow):
    $SHARED_BRANCH -> git pull -> feature/claude$i-xxx -> code -> lint -> PUSH -> CREATE PR -> REVIEW -> MERGE
    
    Specifically:
    - git checkout $SHARED_BRANCH
    - git pull origin $SHARED_BRANCH
    - ALWAYS git checkout -b feature/claude$i-[description]  # Note: claude$i prefix required
    - ALWAYS Make your changes on feature/fix branch of $SHARED_BRANCH
    - DO NOT make changes directly on $SHARED_BRANCH
    - Add analytics to the new code if appropriate
    - Add a unit test under tests/ for the new code
    - Run lint/check commands: $LINT_CMD
    - For javascript projects: $TYPECHECK_CMD
    - git add --all (stage your feature/claude$i-xxx changes)
    - git commit -m \"Claude $i: [description]\" (commit to your feature/claude$i-xxx branch)
    - git push -u origin feature/claude$i-[description] (push feature branch)
    - CREATE PR using provided GitHub URL (MANDATORY STEP)
    - Task complete - PR is ready for review
    - For next task: git checkout $SHARED_BRANCH && git pull origin $SHARED_BRANCH

  ### Workflow for PRs:
  - Same setup: git checkout $SHARED_BRANCH && git pull origin $SHARED_BRANCH
  - Same branch creation: git checkout -b feature/claude$i-[description]
  - Same development: make changes, add tests, run lint/typecheck
  - Same commit: git add --all && git commit -m \"Claude $i: [description]\"
  - Push feature branch: git push -u origin feature/claude$i-[description]
  - Create PR using provided GitHub URL
  - Task complete - PR is ready for review
  - For next task: git checkout $SHARED_BRANCH && git pull origin $SHARED_BRANCH
  
  ### PR Creation Steps (when enabled):
  After pushing your branch, the git hook will display:
  1. **GitHub PR URL** - Click to open PR creation page
  2. **Suggested title** - \"Claude $i: [description]\"
  3. **Copy-paste description** - Pre-formatted PR body
  4. **Testing checklist** - Markdown checklist to copy

  GitHub will auto-detect the branch comparison and pre-populate most fields.
  
  ### Branch naming for PRs:
  - feature/claude$i-[short-description]
  - fix/claude$i-[bug-description]  
  - chore/claude$i-[maintenance-task]
  
  Commit format: Claude $i: what you did
  
  ## Why this PR workflow matters
  - **CI/CD Integration**: Runway automatically tests all PRs
  - **Review Gate**: Human review prevents AI mistakes
  - **Audit Trail**: Clear history of all changes
  - **Conflict Prevention**: PRs show merge conflicts clearly
  - **Branch Protection**: $SHARED_BRANCH stays stable
  
  Last time someone skipped this: 3 days of work lost
  Your current directory is your workspace, but $SHARED_BRANCH is the truth
  
  ## After coding reminders
  - Run $TREE_SCRIPT if files changed
  - Fix any lint warnings
  - Fix any npx tsc errors
  - Regenerate symbol index: ctags -R --exclude=node_modules --exclude=.git .
  - Mention what changed and any merge issues
  
  ## Symbol Index Available
  A ctags file called tags contains all symbols in the codebase. 
  Regenerate the tags symbol index: ctags -R --exclude=node_modules --exclude=.git .
  BEFORE searching files, use: \\\grep \\\"symbolName\\\" tags\\\
  
  ## Development approach
  - Edit existing files (dont create new ones)
  - No docs unless asked
  - Quick fixes still need the git workflow
  
  ## Command execution guidelines (avoid approval prompts)
 ## Temp file handling - ALWAYS use .claude/tmp/
  For ALL temporary files, use the project's .claude/tmp/ directory:
  - Create if needed: mkdir -p .claude/tmp
  - Use: echo data > .claude/tmp/analysis.txt
  - NOT: echo data > /tmp/analysis.txt
  Examples:
  - Search results: grep -r pattern > .claude/tmp/search_results.txt
  - File lists: find . -name *.js > .claude/tmp/js_files.txt
  - Analysis output: npm run lint > .claude/tmp/lint_output.txt
  - Intermediate processing: sort data.txt > .claude/tmp/sorted.txt
  This directory is gitignored and avoids approval prompts.
  Clean up when done: rm .claude/tmp/*.txt
  
  ## Use internal tools to avoid permission prompts
  NEVER use bash redirections - use internal tools instead:
  For searching:
  - BEFORE searching files, use: \\\grep \\\"symbolName\\\" tags\\\
  - BAD: grep -r \\\"pattern\\\" > results.txt
  - GOOD: Use Grep(pattern: \\\"pattern\\\") tool directly
  For file listings:
  - BAD: find . -name \\\"*.js\\\" > files.txt
  - GOOD: Use Glob(pattern: \\\"**/*.js\\\") tool directly
  For reading file sections:
  - BAD: head -n 100 file.txt > excerpt.txt
  - GOOD: Use Read(file_path: \\\"file.txt\\\", limit: 100)
  For creating files:
  - BAD: echo \\\"content\\\" > newfile.txt
  - GOOD: Read(\\\"newfile.txt\\\") then Write(file_path: \\\"newfile.txt\\\", 
  content: \\\"content\\\")
  For complex searches:
  - BEFORE searching files, use: \\\grep \\\"symbolName\\\" tags\\\
  - BAD: Multiple bash commands with temp files
  - GOOD: Use Task tool for complex multi-step searches
  Remember: Internal tools (Read, Write, Grep, Glob, Task) never need 
  permission.
  Bash with redirections (>, >>, <) always needs permission.
  This directory is gitignored and avoids approval prompts.
  Clean up when done: rm .claude/tmp/*.txt
  Remember: Pipes are your friend. Chain commands instead of temp files.
  
  ## Context7 MCP Server Usage
  Context7 provides documentation for libraries. Usage pattern:
  1. Search: mcp__context7__resolve-library-id(libraryName: \\\"mongoose\\\")
  2. Find the library ID in results (e.g., /automattic/mongoose)
  3. Fetch: mcp__context7__get-library-docs(context7CompatibleLibraryID: \\\"/automattic/mongoose\\\")
  
  IMPORTANT Context7 tips:
  - Search is very fuzzy - returns many unrelated results
  - If search shows \\\"Code Snippets: N\\\" then docs ARE available
  - DO NOT specify optional parameters (tokens, topic) unless needed
  - Just use the library ID alone for best results
  - Not all libraries are indexed yet
  
  Working example:
  - Search for \\\"mongoose\\\" → returns /automattic/mongoose with 440 snippets
  - Fetch with just ID → returns comprehensive Mongoose documentation
  
  Common mistake:
  - BAD: get-library-docs(ID: \\\"/lib/name\\\", tokens: 2000) → fails
  - GOOD: get-library-docs(ID: \\\"/lib/name\\\") → works
  
## file-system MCP server usage
  - Use the filesystem MCP server to read, write  or search files in the project directory.
  - Avoid using bash commands with redirections (>, >>, <) as they require permission.
EOF"
echo "   • Wrote project memory: CLAUDE.md"

  # 2.c) Local memory
  run_cmd "cat > '$CLONE_DIR/CLAUDE.local.md' <<EOF
- During coding, add analytics if appropriate
- After coding: write unit tests that run if appropriate
- After coding: run directory_tree.sh if files were added or deleted.
- After coding: run '${LINT_CMD}' and fix warnings.
- For JS/TS/React projects: run '${TYPECHECK_CMD}' to check types.
- Project type: ${PROJECT_TYPE}
EOF"
  echo "   • Wrote local memory: CLAUDE.local.md"

  # 2.d) Settings.json with framework-specific permissions
  ALLOW_LIST='"Bash(git add:*)",
        "Bash(git merge:*)",
        "Bash(git pull:*)",
        "Bash(git push:*)",
        "Bash(git checkout:*)",
        "Bash(git commit:*)",
        "Bash(git stash:*)",
        "Bash(git fetch:*)",
        "Bash(rm:*)",
        "Bash(mkdir:*)",
        "Bash(find:*)",
        "Bash(ctags:*)",
        "Edit(*)",
        "Edit(.claude/tmp/**)",
        "Read(*)",
        "Read(.claude/tmp/**)",
        "Search(*)",
        "Search(pattern: *)",
        "Write(*)",
        "Bash(ls:*)",
        "Bash(git ls-tree:*)",
        "Bash(rg:*)"'
  
  case "$PROJECT_TYPE" in
    javascript|typescript|react|react-native)
      ALLOW_LIST="${ALLOW_LIST},
        \"Bash(npm install:*)\",
        \"Bash(npm test:*)\",
        \"Bash(npm run lint)\",
        \"Bash(npx tsc:*)\""
      ;;
    flutter|dart)
      ALLOW_LIST="${ALLOW_LIST},
        \"Bash(flutter analyze)\",
        \"Bash(flutter test)\",
        \"Bash(dart analyze)\""
      ;;
    rust)
      ALLOW_LIST="${ALLOW_LIST},
        \"Bash(cargo clippy)\",
        \"Bash(cargo test)\""
      ;;
    go)
      ALLOW_LIST="${ALLOW_LIST},
        \"Bash(go vet:*)\",
        \"Bash(go test:*)\""
      ;;
    python)
      ALLOW_LIST="${ALLOW_LIST},
        \"Bash(pytest:*)\",
        \"Bash(mypy:*)\",
        \"Bash(flake8:*)\",
        \"Bash(pylint:*)\""
      ;;
  esac
  
  run_cmd "cat > '$CLONE_DIR/.claude/settings.json' <<EOF
  {
    \"env\": {\"CLAUDE_CODE_ENABLE_TELEMETRY\": \"0\"},
    \"permissions\": {
      \"allow\": [
        $ALLOW_LIST
      ],
      \"deny\": []
    }
  }
EOF"
  run_cmd "cd '$CLONE_DIR' && claude config add allowedTools '[*]'"
  run_cmd "cd '$CLONE_DIR' && claude config add allowedTools 'Search(pattern: *)'"
  run_cmd "cd '$CLONE_DIR' && claude config add allowedTools 'Edit(*)'"
  run_cmd "cd '$CLONE_DIR' && claude config add allowedTools 'Write(*)'"
  run_cmd "cd '$CLONE_DIR' && claude config add allowedTools 'Read(*)'"

  echo "   • Wrote settings.json: $CLONE_DIR/.claude/settings.json"

  # 2.e) start.sh Launcher
  run_cmd "cat > '$CLONE_DIR/start.sh' <<EOF
#!/opt/homebrew/bin/bash
set -euo pipefail
# Make sure NVM_DIR is set, if not, default to \$HOME/.nvm
export NVM_DIR=\"\${NVM_DIR:-\$HOME/.nvm}\"

if [ -s \"\$NVM_DIR/nvm.sh\" ]; then
  # shellcheck source=/dev/null
  . \"\$NVM_DIR/nvm.sh\"
else
  echo \"Error: NVM script not found at \$NVM_DIR/nvm.sh\" >&2
  echo \"Please check your NVM installation and NVM_DIR.\" >&2
  exit 1
fi
cd '$CLONE_DIR'
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
EOF"
  run_cmd "chmod +x '$CLONE_DIR/start.sh'"
  echo "   • Wrote starter script: $CLONE_DIR/start.sh"

   # 2.f) Git Hooks Setup
  echo "   • Setting up git hooks for Agent $i..."

  run_cmd "mkdir -p '$CLONE_DIR/.githooks'"

  # 2.f.1) pre-commit
  precommit_path="$CLONE_DIR/.githooks/pre-commit"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$precommit_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/pre-commit"
    echo "# Enforces:"
    echo "# 1. No direct commits to \$SHARED_BRANCH."
    echo "# 2. Prevent commits on feature/fix branches already merged into \$SHARED_BRANCH."
    echo "# 3. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before committing."
    echo "# 4. Runs lint and type checks."
    echo ""
    echo "# Variables passed from the setup script"
    echo "SHARED_BRANCH=\"$SHARED_BRANCH\""
    echo "AGENT_NUM=\"$i\""
    echo "LINT_CMD=\"$LINT_CMD\""
    echo "TYPECHECK_CMD=\"$TYPECHECK_CMD\""
    echo "PROJECT_TYPE=\"$PROJECT_TYPE\""
    echo ""
    echo "# Variables evaluated when this hook runs"
    echo "current_branch=\$(git rev-parse --abbrev-ref HEAD)"
    echo ""
    echo "# 1) Prevent commits on shared branch"
    echo "if [ \"\$current_branch\" = \"\$SHARED_BRANCH\" ]; then"
    echo "  echo \"ERROR: Direct commits to \$SHARED_BRANCH are forbidden!\""
    echo "  echo \"Claude \$AGENT_NUM: You must create a feature/fix branch first:\""
    echo "  echo \"  git checkout -b feature/your-feature-name\""
    echo "  exit 1"
    echo "fi"
    echo ""
    # REVISION: Implementing the user's requested logic for Rule 2 (pre-commit)
    echo "# 2) Prevent commits if current branch has already been fully merged into shared branch"
    echo "if [[ \"\$current_branch\" =~ ^(feature|fix)/ ]]; then"
    echo "  echo \"Claude \$AGENT_NUM: Checking if '\$current_branch' has already been fully merged into '\$SHARED_BRANCH' or if it's the first commit...\""
    echo "  git fetch origin \"\$SHARED_BRANCH\" >/dev/null 2>&1"
    echo ""
    echo "  BRANCH_BASE=\$(git merge-base \"\$SHARED_BRANCH\" HEAD)"
    echo "  BRANCH_COMMITS=\$(git rev-list --count \"\$BRANCH_BASE\"..HEAD)"
    echo ""
    echo "  if [ \"\$BRANCH_COMMITS\" -eq 0 ]; then"
    echo "    echo \"Claude \$AGENT_NUM: This appears to be the first commit on new branch '\$current_branch' - proceeding.\" >&2"
    echo "  else"
    echo "    REMOTE_SHARED_SHA=\$(git rev-parse \"origin/\$SHARED_BRANCH\" 2>/dev/null || echo \"\")"
    echo ""
    echo "    if [[ -n \"\$REMOTE_SHARED_SHA\" ]]; then"
    echo "      CURRENT_HEAD_SHA=\$(git rev-parse HEAD)"
    echo ""
    echo "      if git merge-base --is-ancestor \"\$CURRENT_HEAD_SHA\" \"\$REMOTE_SHARED_SHA\" && \\"
    echo "         [ \"\$CURRENT_HEAD_SHA\" != \"\$REMOTE_SHARED_SHA\" ]; then"
    echo "        echo \"ERROR: Branch '\$current_branch' has been fully merged into '\$SHARED_BRANCH' or is outdated.\" >&2"
    echo "        echo \"Claude \$AGENT_NUM: No further changes allowed on this merged branch.\" >&2"
    echo "        echo \"  Please create a *new branch* for additional work.\" >&2"
    echo "        exit 1"
    echo "      fi"
    echo "    fi"
    echo "  fi"
    echo "fi"
    echo ""
    echo "# 3) Ensure local shared branch is up-to-date before any commit on feature/fix branch."
    echo "if git show-ref --verify --quiet \"refs/heads/\$SHARED_BRANCH\"; then"
    echo "  echo \"Claude \$AGENT_NUM: Checking if \$SHARED_BRANCH is up-to-date...\""
    echo "  git fetch origin \"\$SHARED_BRANCH\" >/dev/null 2>&1"
    echo "  LOCAL_SHARED=\$(git rev-parse \"\$SHARED_BRANCH\")"
    echo "  REMOTE_SHARED=\$(git rev-parse \"origin/\$SHARED_BRANCH\")"
    echo "  if [ \"\$LOCAL_SHARED\" != \"\$REMOTE_SHARED\" ]; then"
    echo "    echo \"ERROR: Your local '\$SHARED_BRANCH' is not updated with origin/\$SHARED_BRANCH.\" >&2"
    echo "    echo \"Claude \$AGENT_NUM: You need to 'git pull origin \$SHARED_BRANCH' before committing.\" >&2"
    echo "    exit 1"
    echo "  fi"
    echo "fi"
    echo ""
    echo "# 4) Run lint checks"
    echo "echo \"Claude \$AGENT_NUM: Running lint checks...\""
    echo "eval \"\$LINT_CMD\" || {"
    echo "  echo \"ERROR: Lint failed! Fix errors above before committing.\" >&2"
    echo "  exit 1"
    echo "}"
    echo ""
    echo "if [[ \"\$PROJECT_TYPE\" =~ ^(javascript|typescript|react|react-native)$ ]]; then"
    echo "  echo \"Claude \$AGENT_NUM: Running type checks...\""
    echo "  eval \"\$TYPECHECK_CMD\" || {"
    echo "    echo \"ERROR: Type check failed! Fix errors above before committing.\" >&2"
    echo "    exit 1"
    echo "  }"
    echo "fi"
    echo ""
    echo "echo \"Claude \$AGENT_NUM: Pre-commit checks passed ✓\""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$precommit_path" <<EOF
#!/bin/bash
# .githooks/pre-commit
# Enforces:
# 1. No direct commits to \$SHARED_BRANCH.
# 2. Prevent commits on feature/fix branches already merged into \$SHARED_BRANCH.
# 3. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before committing.
# 4. Runs lint and type checks.

# Variables passed from the setup script
SHARED_BRANCH="$SHARED_BRANCH"
AGENT_NUM="$i"
LINT_CMD="$LINT_CMD"
TYPECHECK_CMD="$TYPECHECK_CMD"
PROJECT_TYPE="$PROJECT_TYPE"

# Variables evaluated when this hook runs
current_branch=\$(git rev-parse --abbrev-ref HEAD)

# 1) Prevent commits on shared branch
if [ "\$current_branch" = "\$SHARED_BRANCH" ]; then
  echo "ERROR: Direct commits to \$SHARED_BRANCH are forbidden!" >&2
  echo "Claude \$AGENT_NUM: You must create a feature/fix branch first:" >&2
  echo "  git checkout -b feature/your-feature-name" >&2
  exit 1
fi

# REVISION: Implementing the user's requested logic for Rule 2 (pre-commit)
# 2) Prevent commits if current branch has already been fully merged into shared branch
if [[ "\$current_branch" =~ ^(feature|fix)/ ]]; then
  echo "Claude \$AGENT_NUM: Checking if '\$current_branch' has already been fully merged into '\$SHARED_BRANCH' or if it's the first commit..."
  git fetch origin "\$SHARED_BRANCH" >/dev/null 2>&1

  BRANCH_BASE=\$(git merge-base "\$SHARED_BRANCH" HEAD)
  BRANCH_COMMITS=\$(git rev-list --count "\$BRANCH_BASE"..HEAD)

  if [ "\$BRANCH_COMMITS" -eq 0 ]; then
    # This is the very first commit on this feature/fix branch (relative to SHARED_BRANCH base)
    echo "Claude \$AGENT_NUM: This appears to be the first commit on new branch '\$current_branch' - proceeding." >&2
  else
    # This is not the first commit, so check if it's already merged/outdated
    REMOTE_SHARED_SHA=\$(git rev-parse "origin/\$SHARED_BRANCH" 2>/dev/null || echo "")

    if [[ -n "\$REMOTE_SHARED_SHA" ]]; then
      CURRENT_HEAD_SHA=\$(git rev-parse HEAD)

      if git merge-base --is-ancestor "\$CURRENT_HEAD_SHA" "\$REMOTE_SHARED_SHA" && \
         [ "\$CURRENT_HEAD_SHA" != "\$REMOTE_SHARED_SHA" ]; then
        echo "ERROR: Branch '\$current_branch' has been fully merged into '\$SHARED_BRANCH' or is outdated." >&2
        echo "Claude \$AGENT_NUM: No further changes allowed on this merged branch." >&2
        echo "  Please create a *new branch* for additional work." >&2
        exit 1
      fi
    fi
  fi
fi

# 3) Ensure local shared branch is up-to-date before any commit on feature/fix branch.
if git show-ref --verify --quiet "refs/heads/\$SHARED_BRANCH"; then
  echo "Claude \$AGENT_NUM: Checking if \$SHARED_BRANCH is up-to-date..."
  git fetch origin "\$SHARED_BRANCH" >/dev/null 2>&1
  LOCAL_SHARED=\$(git rev-parse "\$SHARED_BRANCH")
  REMOTE_SHARED=\$(git rev-parse "origin/\$SHARED_BRANCH")

  if [ "\$LOCAL_SHARED" != "\$REMOTE_SHARED" ]; then
    echo "ERROR: Your local '\$SHARED_BRANCH' is not updated with origin/\$SHARED_BRANCH." >&2
    echo "Claude \$AGENT_NUM: You need to 'git pull origin \$SHARED_BRANCH' before committing." >&2
    exit 1
  fi
fi

# 4) Run lint checks
echo "Claude \$AGENT_NUM: Running lint checks..."
eval "\$LINT_CMD" || {
  echo "ERROR: Lint failed! Fix errors above before committing." >&2
  exit 1
}

if [[ "\$PROJECT_TYPE" =~ ^(javascript|typescript|react|react-native)$ ]]; then
  echo "Claude \$AGENT_NUM: Running type checks..."
  eval "\$TYPECHECK_CMD" || {
    echo "ERROR: Type check failed! Fix errors above before committing." >&2
    exit 1
  }
fi

echo "Claude \$AGENT_NUM: Pre-commit checks passed ✓"
exit 0
EOF
  fi
  run_cmd "chmod +x '$precommit_path'"

  # 2.f.2) commit-msg
  commitmsg_path="$CLONE_DIR/.githooks/commit-msg"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$commitmsg_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/commit-msg"
    echo "# Enforces:"
    echo "# 1. Commit message starts with \"Claude \$AGENT_NUM:\"."
    echo "# 2. No direct commits to \$SHARED_BRANCH—unless it’s a merge commit in progress."
    echo ""
    echo "# Variables passed from the setup script"
    echo "SHARED_BRANCH=\"$SHARED_BRANCH\""
    echo "AGENT_NUM=\"$i\""
    echo ""
    echo "# Variables evaluated when this hook runs"
    echo "BRANCH=\$(git rev-parse --abbrev-ref HEAD)"
    echo ""
    echo "# If on shared branch, allow only merge commits (detect via MERGE_HEAD)."
    echo "if [[ \"\$BRANCH\" = \"\$SHARED_BRANCH\" ]]; then"
    echo "  GIT_DIR=\$(git rev-parse --git-dir)"
    echo "  if [ -f \"\$GIT_DIR/MERGE_HEAD\" ]; then"
    echo "    exit 0"
    echo "  fi"
    echo "  echo \"ERROR: You are about to commit directly to '\$SHARED_BRANCH'. This is forbidden.\""
    echo "  echo \"Claude \$AGENT_NUM: Only merge commits are allowed on \$SHARED_BRANCH.\""
    echo "  exit 1"
    echo "fi"
    echo ""
    echo "# Enforce message format \"Claude \$AGENT_NUM: <text>\" for non-merge commits"
    echo "GIT_DIR=\$(git rev-parse --git-dir)"
    echo "if [ ! -f \"\$GIT_DIR/MERGE_HEAD\" ]; then"
    echo "  COMMIT_MSG_FILE=\"\$1\""
    echo "  FIRST_LINE=\$(head -n1 \"\$COMMIT_MSG_FILE\")"
    echo "  if ! [[ \"\$FIRST_LINE\" =~ ^Claude\\ [0-9]+:\\  ]]; then"
    echo "    echo \"ERROR: Commit message must start with 'Claude \$AGENT_NUM: <description>'\""
    echo "    echo \"Example: Claude \$AGENT_NUM: feat(feature): Implement new widget\""
    echo "    exit 1"
    echo "  fi"
    echo "fi"
    echo ""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$commitmsg_path" <<EOF
#!/bin/bash
# .githooks/commit-msg
# Enforces:
# 1. Commit message starts with "Claude \$AGENT_NUM:".
# 2. No direct commits to \$SHARED_BRANCH—unless it’s a merge commit in progress.

# Variables passed from the setup script
SHARED_BRANCH="$SHARED_BRANCH"
AGENT_NUM="$i"

# Variables evaluated when this hook runs
BRANCH=\$(git rev-parse --abbrev-ref HEAD)

# If on shared branch, allow only merge commits (detect via MERGE_HEAD).
if [[ "\$BRANCH" = "\$SHARED_BRANCH" ]]; then
  GIT_DIR=\$(git rev-parse --git-dir)
  # If MERGE_HEAD exists, we are completing a merge—allow that.
  if [ -f "\$GIT_DIR/MERGE_HEAD" ]; then
    exit 0
  fi
  echo "ERROR: You are about to commit directly to '\$SHARED_BRANCH'. This is forbidden." >&2
  echo "Claude \$AGENT_NUM: Only merge commits are allowed on \$SHARED_BRANCH." >&2
  exit 1
fi

# Enforce message format "Claude \$AGENT_NUM: <text>" for non-merge commits
GIT_DIR=\$(git rev-parse --git-dir)
if [ ! -f "\$GIT_DIR/MERGE_HEAD" ]; then
  COMMIT_MSG_FILE="\$1"
  FIRST_LINE=\$(head -n1 "\$COMMIT_MSG_FILE")
  if ! [[ "\$FIRST_LINE" =~ ^Claude\ [0-9]+:\  ]]; then
    echo "ERROR: Commit message must start with 'Claude \$AGENT_NUM: <description>'" >&2
    echo "Example: Claude \$AGENT_NUM: feat(feature): Implement new widget" >&2
    exit 1
  fi
fi

exit 0
EOF
  fi
  run_cmd "chmod +x '$commitmsg_path'"

  # 2.f.3) pre-merge-commit
  premerge_path="$CLONE_DIR/.githooks/pre-merge-commit"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$premerge_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/pre-merge-commit"
    echo "# Enforces:"
    echo "# 1. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before merging into it."
    echo ""
    echo "# Variables passed from the setup script"
    echo "SHARED_BRANCH=\"$SHARED_BRANCH\""
    echo "AGENT_NUM=\"$i\""
    echo ""
    echo "# Variables evaluated when this hook runs"
    echo "TARGET_BRANCH=\$(git rev-parse --abbrev-ref HEAD)"
    echo ""
    echo "# Only apply this check when merging into the SHARED_BRANCH"
    echo "if [[ \"\$TARGET_BRANCH\" != \"\$SHARED_BRANCH\" ]]; then"
    echo "  exit 0"
    echo "fi"
    echo ""
    echo "echo \"Claude \$AGENT_NUM: Checking if \$SHARED_BRANCH is up-to-date before finalizing merge...\""
    echo "git fetch origin \"\$SHARED_BRANCH\" >/dev/null 2>&1"
    echo ""
    echo "LOCAL=\$(git rev-parse \"\$SHARED_BRANCH\")"
    echo "REMOTE=\$(git rev-parse \"origin/\$SHARED_BRANCH\")"
    echo ""
    echo "if [ \"\$LOCAL\" != \"\$REMOTE\" ]; then"
    echo "  echo \"ERROR: Your local '\$SHARED_BRANCH' is behind 'origin/\$SHARED_BRANCH'.\""
    echo "  echo \"Claude \$AGENT_NUM: You must 'git pull origin \$SHARED_BRANCH' before merging changes into it.\""
    echo "  exit 1"
    echo "fi"
    echo ""
    echo "echo \"Claude \$AGENT_NUM: Pre-merge-commit checks passed ✓\""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$premerge_path" <<EOF
#!/bin/bash
# .githooks/pre-merge-commit
# Enforces:
# 1. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before merging into it.

# Variables passed from the setup script
SHARED_BRANCH="$SHARED_BRANCH"
AGENT_NUM="$i"

# Variables evaluated when this hook runs
TARGET_BRANCH=\$(git rev-parse --abbrev-ref HEAD)

# Only apply this check when merging into the SHARED_BRANCH
if [[ "\$TARGET_BRANCH" != "\$SHARED_BRANCH" ]]; then
  exit 0
fi

echo "Claude \$AGENT_NUM: Checking if \$SHARED_BRANCH is up-to-date before finalizing merge..."
git fetch origin "\$SHARED_BRANCH" >/dev/null 2>&1

LOCAL=\$(git rev-parse "\$SHARED_BRANCH")
REMOTE=\$(git rev-parse "origin/\$SHARED_BRANCH")

if [ "\$LOCAL" != "\$REMOTE" ]; then
  echo "ERROR: Your local '\$SHARED_BRANCH' is behind 'origin/\$SHARED_BRANCH'." >&2
  echo "Claude \$AGENT_NUM: You must 'git pull origin \$SHARED_BRANCH' before merging changes into it." >&2
  exit 1
fi

echo "Claude \$AGENT_NUM: Pre-merge-commit checks passed ✓"
exit 0
EOF
  fi
  run_cmd "chmod +x '$premerge_path'"

  # 2.f.4) pre-push
  prepull_path="$CLONE_DIR/.githooks/pre-push"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$prepull_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/pre-push"
    echo "# Enforces:"
    echo "# 1. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before pushing it."
    echo "# 2. Prevent pushing new commits to feature/fix branches already merged into \$SHARED_BRANCH."
    echo ""
    echo "# Variables passed from the setup script"
    echo "SHARED_BRANCH=\"$SHARED_BRANCH\""
    echo "AGENT_NUM=\"$i\""
    echo ""
    echo "# Fetch shared branch to ensure remote comparison is accurate"
    echo "echo \"Claude \$AGENT_NUM: Pre-push hook: Fetching origin/\$SHARED_BRANCH for up-to-date checks...\""
    echo "git fetch origin \"\$SHARED_BRANCH\" >/dev/null 2>&1 || {"
    echo "  echo \"ERROR: Failed to fetch origin/\$SHARED_BRANCH. Cannot perform push validation.\""
    echo "  exit 1"
    echo "}"
    echo ""
    echo "# Loop through all refs being pushed"
    echo "while read local_ref local_sha remote_ref remote_sha_before_push"
    echo "do"
    echo "  branch_name=\$(echo \"\$local_ref\" | sed 's|^refs/heads/||')" 
    echo ""
    # REVISION: Rule 1 logic for SHARED_BRANCH push
    echo "  if [ \"\$branch_name\" = \"\$SHARED_BRANCH\" ]; then"
    echo "    echo \"Claude \$AGENT_NUM: Checking for remote updates on '\$SHARED_BRANCH' before push...\""
    echo "    LOCAL_HEAD_SHA=\"\$local_sha\""
    echo "    REMOTE_TRACKING_SHA=\$(git rev-parse \"\$REMOTE_NAME/\$SHARED_BRANCH\" 2>/dev/null || echo \"\")"
    echo ""
    echo "    if [ -z \"\$REMOTE_TRACKING_SHA\" ]; then"
    echo "        echo \"Claude \$AGENT_NUM: Remote branch '$REMOTE_NAME/\$SHARED_BRANCH' does not exist. Allowing initial push.\" >&2"
    echo "        continue # Allow initial push of the shared branch"
    echo "    fi"
    echo ""
    echo "    AHEAD_COMMITS=\$(git rev-list --count \"\$REMOTE_TRACKING_SHA\"..\"\$LOCAL_HEAD_SHA\")"
    echo "    BEHIND_COMMITS=\$(git rev-list --count \"\$LOCAL_HEAD_SHA\"..\"\$REMOTE_TRACKING_SHA\")"
    echo ""
    echo "    if [ \"\$BEHIND_COMMITS\" -gt 0 ]; then"
    echo "        if [ \"\$AHEAD_COMMITS\" -gt 0 ]; then"
    echo "            echo \"ERROR: Your local '\$SHARED_BRANCH' is divergent from '$REMOTE_NAME/\$SHARED_BRANCH'.\" >&2"
    echo "            echo \"Claude \$AGENT_NUM: Your branch is ahead by \$AHEAD_COMMITS commits and behind by \$BEHIND_COMMITS commits.\" >&2"
    echo "            echo \"Claude \$AGENT_NUM: You must rebase or merge: git pull --rebase $REMOTE_NAME \$SHARED_BRANCH (recommended for shared branches)\" >&2"
    echo "            echo \"(Note: Even if 'git pull' *seems* to say 'Already up to date', the remote branch has new changes.)\" >&2" # New clarifying message
    echo "            exit 1"
    echo "        else"
    echo "            echo \"ERROR: Remote \$SHARED_BRANCH has new changes! Your local '\$SHARED_BRANCH' is behind '$REMOTE_NAME/\$SHARED_BRANCH' by \$BEHIND_COMMITS commits.\" >&2"
    echo "            echo \"Claude \$AGENT_NUM: You must pull first: git pull $REMOTE_NAME \$SHARED_BRANCH\" >&2"
    echo "            echo \"(Note: Even if 'git pull' *seems* to say 'Already up to date', the remote branch has new changes.)\" >&2" # New clarifying message
    echo "            exit 1"
    echo "        fi"
    echo "    fi"
    echo "    echo \"Claude \$AGENT_NUM: Push validation for \$SHARED_BRANCH passed ✓\""
    echo "    continue"
    echo "  fi"
    echo ""
    echo "# Rule 2: Prevent pushing new commits to already merged feature/fix branches"
    echo "  if [[ \"\$branch_name\" =~ ^(feature|fix)/ ]]; then"
    echo "    echo \"Claude \$AGENT_NUM: Validating push for branch '\$branch_name' (merged-branch check)...\""
    echo ""
    echo "    if [ \"\$remote_sha_before_push\" != \"0000000000000000000000000000000000000000\" ]; then"
    echo "      # This branch already exists on remote. Check if its remote tip was already merged."
    echo "      if git merge-base --is-ancestor \"\$remote_sha_before_push\" \"origin/\$SHARED_BRANCH\"; then"
    echo "        # If it was merged AND there are new commits being pushed, block."
    echo "        if [ \"\$local_sha\" != \"\$remote_sha_before_push\" ]; then"
    echo "          echo \"ERROR: Attempting to push new commits to branch '\$branch_name'.\" >&2"
    echo "          echo \"Claude \$AGENT_NUM: This branch has already been officially merged into 'origin/\$SHARED_BRANCH'.\" >&2"
    echo "          echo \"  Further commits to this branch are not permitted.\" >&2"
    echo "          echo \"  Create a new branch for follow-up work.\" >&2"
    echo "          echo \"  Delete old branch: 'git branch -d \$branch_name' and 'git push origin --delete \$branch_name'.\" >&2"
    echo "          exit 1"
    echo "        fi"
    echo "      fi"
    echo "    fi"
    echo "  fi"
    echo "done < /dev/stdin"
    echo ""
    echo "echo \"Claude \$AGENT_NUM: All pre-push checks passed ✓\""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$prepull_path" <<EOF
#!/bin/bash
# .githooks/pre-push
# Enforces:
# 1. Local \$SHARED_BRANCH is up-to-date with origin/\$SHARED_BRANCH before pushing it.
# 2. Prevent pushing new commits to feature/fix branches already merged into \$SHARED_BRANCH.

# Variables passed from the setup script
SHARED_BRANCH="$SHARED_BRANCH"
AGENT_NUM="$i"

# Fetch shared branch to ensure remote comparison is accurate
echo "Claude \$AGENT_NUM: Pre-push hook: Fetching origin/\$SHARED_BRANCH for up-to-date checks..."
git fetch origin "\$SHARED_BRANCH" >/dev/null 2>&1 || {
  echo "ERROR: Failed to fetch origin/\$SHARED_BRANCH. Cannot perform push validation." >&2
  exit 1
}

# Loop through all refs being pushed
# Input: <local-ref> <local-sha> <remote-ref> <remote-sha-before-push>
while read local_ref local_sha remote_ref remote_sha_before_push
do
  branch_name=\$(echo "\$local_ref" | sed 's|^refs/heads/||')

  if [ "\$branch_name" = "\$SHARED_BRANCH" ]; then
    echo "Claude \$AGENT_NUM: Checking for remote updates on '\$SHARED_BRANCH' before push..."
    LOCAL_HEAD_SHA="\$local_sha"
    REMOTE_TRACKING_SHA=\$(git rev-parse "\$REMOTE_NAME/\$SHARED_BRANCH" 2>/dev/null || echo "")

    if [ -z "\$REMOTE_TRACKING_SHA" ]; then
        # Remote shared branch does not exist yet (e.g., first push of claude0 branch)
        echo "Claude \$AGENT_NUM: Remote branch '$REMOTE_NAME/\$SHARED_BRANCH' does not exist. Allowing initial push." >&2
        continue # Allow initial push of the shared branch
    fi

    AHEAD_COMMITS=\$(git rev-list --count "\$REMOTE_TRACKING_SHA".."\$LOCAL_HEAD_SHA")
    BEHIND_COMMITS=\$(git rev-list --count "\$LOCAL_HEAD_SHA".."\$REMOTE_TRACKING_SHA")

    if [ "\$BEHIND_COMMITS" -gt 0 ]; then
        if [ "\$AHEAD_COMMITS" -gt 0 ]; then
            # Divergent state: Local is ahead and behind
            echo "ERROR: Your local '\$SHARED_BRANCH' is divergent from '$REMOTE_NAME/\$SHARED_BRANCH'." >&2
            echo "Claude \$AGENT_NUM: Your branch is ahead by \$AHEAD_COMMITS commits and behind by \$BEHIND_COMMITS commits." >&2
            echo "Claude \$AGENT_NUM: You must rebase or merge: git pull --rebase $REMOTE_NAME \$SHARED_BRANCH (recommended for shared branches)" >&2
            echo "(Note: Even if 'git pull' *seems* to say 'Already up to date', the remote branch has new changes.)" >&2 # New clarifying message
            exit 1
        else
            # Behind state: Local is only behind (0 ahead, >0 behind)
            echo "ERROR: Remote \$SHARED_BRANCH has new changes! Your local '\$SHARED_BRANCH' is behind '$REMOTE_NAME/\$SHARED_BRANCH' by \$BEHIND_COMMITS commits." >&2
            echo "Claude \$AGENT_NUM: You must pull first: git pull $REMOTE_NAME \$SHARED_BRANCH" >&2
            echo "(Note: Even if 'git pull' *seems* to say 'Already up to date', the remote branch has new changes.)" >&2 # New clarifying message
            exit 1
        fi
    fi
    # If we reached here without exiting, it means the push is allowed (e.g., simply ahead or equal).
    echo "Claude \$AGENT_NUM: Push validation for \$SHARED_BRANCH passed ✓"
    continue # Skip to next ref in push loop
  fi

# Rule 2: Prevent pushing new commits to already merged feature/fix branches
  if [[ "\$branch_name" =~ ^(feature|fix)/ ]]; then
    echo "Claude \$AGENT_NUM: Validating push for branch '\$branch_name' (merged-branch check)..."

    if [ "\$remote_sha_before_push" != "0000000000000000000000000000000000000000" ]; then
      # This branch already exists on remote. Check if its remote tip was already merged.
      if git merge-base --is-ancestor "\$remote_sha_before_push" "origin/\$SHARED_BRANCH"; then
        # If it was merged AND there are new commits being pushed, block.
        if [ "\$local_sha" != "\$remote_sha_before_push" ]; then
          echo "ERROR: Attempting to push new commits to branch '\$branch_name'." >&2
          echo "Claude \$AGENT_NUM: This branch has already been officially merged into 'origin/\$SHARED_BRANCH'." >&2
          echo "  Further commits to this branch are not permitted." >&2
          echo "  Create a new branch for follow-up work." >&2
          echo "  Delete old branch: 'git branch -d \$branch_name' and 'git push origin --delete \$branch_name'." >&2
          exit 1
        fi
      fi
    fi
    # For new branches (remote_sha_before_push = 000...), or branches not yet merged, allow push.
  fi
done < /dev/stdin

echo "Claude \$AGENT_NUM: All pre-push checks passed ✓"
exit 0
EOF
  fi
  run_cmd "chmod +x '$prepull_path'"

  # 2.f.5) post-commit
  postcommit_path="$CLONE_DIR/.githooks/post-commit"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$postcommit_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/post-commit"
    echo "# Reminds agent to push their feature/fix branch after a commit."
    echo ""
    echo "# Variables passed from the setup script"
    echo "SHARED_BRANCH=\"$SHARED_BRANCH\""
    echo "AGENT_NUM=\"$i\""
    echo ""
    echo "# Variables evaluated when this hook runs"
    echo "CURRENT_BRANCH=\$(git rev-parse --abbrev-ref HEAD)"
    echo ""
    echo "# If not on the shared branch, provide a reminder to push the feature/fix branch"
    echo "if [[ \"\$CURRENT_BRANCH\" != \"\$SHARED_BRANCH\" ]]; then"
    echo "  echo"
    echo "  echo \"🔔 Claude \$AGENT_NUM: You just committed to '\$CURRENT_BRANCH'.\""
    echo "  echo \"   If you haven’t already, push your feature/fix branch now:\""
    echo "  echo \"   → git push -u origin \$CURRENT_BRANCH\""
    echo "  echo"
    echo "fi"
    echo ""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$postcommit_path" <<EOF
#!/bin/bash
# .githooks/post-commit
# Reminds agent to push their feature/fix branch after a commit.

# Variables passed from the setup script
SHARED_BRANCH="$SHARED_BRANCH"
AGENT_NUM="$i"

# Variables evaluated when this hook runs
CURRENT_BRANCH=\$(git rev-parse --abbrev-ref HEAD)

# If not on the shared branch, provide a reminder to push the feature/fix branch
if [[ "\$CURRENT_BRANCH" != "\$SHARED_BRANCH" ]]; then
  echo
  echo "🔔 Claude \$AGENT_NUM: You just committed to '\$CURRENT_BRANCH'."
  echo "   If you haven’t already, push your feature/fix branch now:"
  echo "   → git push -u origin \$CURRENT_BRANCH"
  echo
fi

exit 0
EOF
  fi
  run_cmd "chmod +x '$postcommit_path'"

  # 2.f.6) post-merge
  postmerge_path="$CLONE_DIR/.githooks/post-merge"
  if [[ "$dry_run" == true ]]; then
    echo "DRY-RUN: cat > '$postmerge_path' <<EOF"
    echo "#!/bin/bash"
    echo "# .githooks/post-merge"
    echo "# Runs housekeeping tasks after a merge:"
    echo "# 1. Updates directory tree."
    echo "# 2. Regenerates ctags."
    echo ""
    echo "# Variables passed from the setup script"
    echo "AGENT_NUM=\"$i\""
    echo "CLONE_DIR=\"$CLONE_DIR\""
    echo "TREE_SCRIPT=\"$TREE_SCRIPT\""
    echo ""
    echo "echo \"Claude \$AGENT_NUM: Merge completed. Running post-merge tasks...\""
    echo ""
    echo "# Regenerate directory tree if script exists"
    echo "if [[ -f \"\$CLONE_DIR/\$TREE_SCRIPT\" ]]; then"
    echo "  echo \"Claude \$AGENT_NUM: Updating directory tree...\""
    echo "  (cd \"\$CLONE_DIR\" && .\/\$TREE_SCRIPT)"
    echo "fi"
    echo ""
    echo "# Regenerate ctags"
    echo "echo \"Claude \$AGENT_NUM: Regenerating symbol index...\""
    echo "(cd \"\$CLONE_DIR\" && ctags -R --exclude=node_modules --exclude=.git .)"
    echo ""
    echo "echo \"Claude \$AGENT_NUM: Post-merge tasks completed ✓\""
    echo "exit 0"
    echo "EOF"
  else
    cat > "$postmerge_path" <<EOF
#!/bin/bash
# .githooks/post-merge
# Runs housekeeping tasks after a merge:
# 1. Updates directory tree.
# 2. Regenerates ctags.

# Variables passed from the setup script
AGENT_NUM="$i"
CLONE_DIR="$CLONE_DIR"
TREE_SCRIPT="$TREE_SCRIPT"

echo "Claude \$AGENT_NUM: Merge completed. Running post-merge tasks..."

# Regenerate directory tree if script exists
if [[ -f "\$CLONE_DIR/\$TREE_SCRIPT" ]]; then
  echo "Claude \$AGENT_NUM: Updating directory tree..."
  (cd "\$CLONE_DIR" && ./"\$TREE_SCRIPT")
fi

# Regenerate ctags
echo "Claude \$AGENT_NUM: Regenerating symbol index..."
(cd "\$CLONE_DIR" && ctags -R --exclude=node_modules --exclude=.git .)

echo "Claude \$AGENT_NUM: Post-merge tasks completed ✓"
exit 0
EOF
  fi
  run_cmd "chmod +x '$postmerge_path'"

  # 2.f.7) Finally, tell Git to use our custom hooks folder
  run_cmd "cd '$CLONE_DIR' && git config core.hooksPath .githooks"

  echo "   • Git hooks configured with core.hooksPath = .githooks"
done

run_cmd "echo 'Setup complete: isolated agents in $PARENT_DIR/${ORIGINAL_PROJECT_NAME}-claude*'"