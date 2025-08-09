# Project memory for Claude Agent 1
  ## CRITICAL: Which agent are you? (1 agents active = confusion)
  
  You are Claude 1 here. The user is running 1 different agents simultaneously 
  and gets confused about who said what. Last week, Claude 3 accidentally overwrote 
  Claude 1's work because the user thought they were talking to Claude 2.
  
  Solution: Start responses with "Claude 1 here" when it matters (first response, 
  after errors, when confirming actions). Not robotic - just clear.
  
  Working in: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1  
  
  ## BEFORE STARTING ANY TASK - MANDATORY CODE UPDATE
  ⚠️  ALWAYS start with these commands for ANY new request:
  - git checkout main
  - git pull origin main
  
  ## TRIGGER WORDS that REQUIRE immediate code update:
  - "bug" / "issue" / "problem" / "error" / "broken"
  - "analyze" / "investigate" / "look at" / "check"
  - "fix" / "update" / "modify" / "change" / "add"
  - "we have" / "there is" / "I see" / "found"
  - ANY request about existing code
  
  ## WHY: Other agents may have made changes since your last pull
  
  ## CORRECT RESPONSE PATTERN:
  User: "We have a bug in xyz, analyze the problem..."
  Claude 1: "Let me first get the latest code from other agents:
  ```bash
  git checkout main
  git pull origin main
  ```
  Now I'll analyze the xyz problem..."
  
  ## BEFORE ANY CODE EDIT - MANDATORY CHECK
  When user asks for ANY code change, your FIRST response MUST be:
  "Claude 1: Starting git workflow for [brief description]"
  Then show the git commands you'll run.
  
  ## DANGER WORDS that trigger git workflow:
  - "make that change"
  - "ok" (after discussing code)
  - "fix"
  - "update" 
  - "add"
  - "implement"
  
  ## MANDATORY: PR-Based Workflow (CI/CD Integration)
  ⚠️  ALL changes must go through Pull Requests for Runway CI/CD integration.
  ⚠️  Direct merges to main are FORBIDDEN.
  
 ## The safe git workflow pattern (memorize this flow):
    main -> git pull -> feature/claude1-xxx -> code -> lint -> PUSH -> CREATE PR -> REVIEW -> MERGE
    
    Specifically:
    - git checkout main
    - git pull origin main
    - ALWAYS git checkout -b feature/claude1-[description]  # Note: claude1 prefix required
    - ALWAYS Make your changes on feature/fix branch of main
    - DO NOT make changes directly on main
    - Add analytics to the new code if appropriate
    - Add a unit test under tests/ for the new code
    - Run lint/check commands: flake8 . || pylint **/*.py
    - For javascript projects: mypy .
    - git add --all (stage your feature/claude1-xxx changes)
    - git commit -m "Claude 1: [description]" (commit to your feature/claude1-xxx branch)
    - git push -u origin feature/claude1-[description] (push feature branch)
    - CREATE PR using provided GitHub URL (MANDATORY STEP)
    - Task complete - PR is ready for review
    - For next task: git checkout main && git pull origin main

  ### Workflow for PRs:
  - Same setup: git checkout main && git pull origin main
  - Same branch creation: git checkout -b feature/claude1-[description]
  - Same development: make changes, add tests, run lint/typecheck
  - Same commit: git add --all && git commit -m "Claude 1: [description]"
  - Push feature branch: git push -u origin feature/claude1-[description]
  - Create PR using provided GitHub URL
  - Task complete - PR is ready for review
  - For next task: git checkout main && git pull origin main
  
  ### PR Creation Steps (when enabled):
  After pushing your branch, the git hook will display:
  1. **GitHub PR URL** - Click to open PR creation page
  2. **Suggested title** - "Claude 1: [description]"
  3. **Copy-paste description** - Pre-formatted PR body
  4. **Testing checklist** - Markdown checklist to copy

  GitHub will auto-detect the branch comparison and pre-populate most fields.
  
  ### Branch naming for PRs:
  - feature/claude1-[short-description]
  - fix/claude1-[bug-description]  
  - chore/claude1-[maintenance-task]
  
  Commit format: Claude 1: what you did
  
  ## Why this PR workflow matters
  - **CI/CD Integration**: Runway automatically tests all PRs
  - **Review Gate**: Human review prevents AI mistakes
  - **Audit Trail**: Clear history of all changes
  - **Conflict Prevention**: PRs show merge conflicts clearly
  - **Branch Protection**: main stays stable
  
  Last time someone skipped this: 3 days of work lost
  Your current directory is your workspace, but main is the truth
  
  ## After coding reminders
  - Run directory_tree.sh if files changed
  - Fix any lint warnings
  - Fix any npx tsc errors
  - Regenerate symbol index: ctags -R --exclude=node_modules --exclude=.git .
  - Mention what changed and any merge issues
  
  ## Symbol Index Available
  A ctags file called tags contains all symbols in the codebase. 
  Regenerate the tags symbol index: ctags -R --exclude=node_modules --exclude=.git .
  BEFORE searching files, use: \grep \"symbolName\" tags\  
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
  - BEFORE searching files, use: \grep \"symbolName\" tags\  - BAD: grep -r \"pattern\" > results.txt
  - GOOD: Use Grep(pattern: \"pattern\") tool directly
  For file listings:
  - BAD: find . -name \"*.js\" > files.txt
  - GOOD: Use Glob(pattern: \"**/*.js\") tool directly
  For reading file sections:
  - BAD: head -n 100 file.txt > excerpt.txt
  - GOOD: Use Read(file_path: \"file.txt\", limit: 100)
  For creating files:
  - BAD: echo \"content\" > newfile.txt
  - GOOD: Read(\"newfile.txt\") then Write(file_path: \"newfile.txt\", 
  content: \"content\")
  For complex searches:
  - BEFORE searching files, use: \grep \"symbolName\" tags\  - BAD: Multiple bash commands with temp files
  - GOOD: Use Task tool for complex multi-step searches
  Remember: Internal tools (Read, Write, Grep, Glob, Task) never need 
  permission.
  Bash with redirections (>, >>, <) always needs permission.
  This directory is gitignored and avoids approval prompts.
  Clean up when done: rm .claude/tmp/*.txt
  Remember: Pipes are your friend. Chain commands instead of temp files.
  
  ## Context7 MCP Server Usage
  Context7 provides documentation for libraries. Usage pattern:
  1. Search: mcp__context7__resolve-library-id(libraryName: \"mongoose\")
  2. Find the library ID in results (e.g., /automattic/mongoose)
  3. Fetch: mcp__context7__get-library-docs(context7CompatibleLibraryID: \"/automattic/mongoose\")
  
  IMPORTANT Context7 tips:
  - Search is very fuzzy - returns many unrelated results
  - If search shows \"Code Snippets: N\" then docs ARE available
  - DO NOT specify optional parameters (tokens, topic) unless needed
  - Just use the library ID alone for best results
  - Not all libraries are indexed yet
  
  Working example:
  - Search for \"mongoose\" → returns /automattic/mongoose with 440 snippets
  - Fetch with just ID → returns comprehensive Mongoose documentation
  
  Common mistake:
  - BAD: get-library-docs(ID: \"/lib/name\", tokens: 2000) → fails
  - GOOD: get-library-docs(ID: \"/lib/name\") → works
  
## file-system MCP server usage
  - Use the filesystem MCP server to read, write  or search files in the project directory.
  - Avoid using bash commands with redirections (>, >>, <) as they require permission.
