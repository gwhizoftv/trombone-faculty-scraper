# Trombone Faculty Scraper Workflow Documentation

## Current Status
- **Progress**: 123/202 universities completed
- **System Version**: V2 with URL tracking and resume capability
- **Last Updated**: August 11, 2025

## Overview
This system automates the process of finding trombone faculty at music schools by:
1. Reading a list of universities from a CSV file
2. Generating prompts for Claude Desktop to search each school's website
3. Launching Claude Desktop via AppleScript to process each school
4. Tracking URLs visited for resume capability if context runs out
5. Saving results to individual CSV files per school

## Core Workflow Files

### 1. Main Orchestrator
**`smart_automated_scraper_v2.sh`**
- Launches Claude Desktop for each university
- Monitors for completion or timeout (3 minutes)
- Handles resume logic if Claude times out
- Moves URL logs to permanent storage on success
- Updates progress tracker

### 2. Prompt Generator
**`generate_simple_resumable_prompt.py`**
- Reads progress from `progress_tracker.txt`
- Checks for existing URL logs to determine if resuming
- Generates appropriate prompts with URL tracking instructions
- Outputs to `current_prompt.txt`

### 3. Input Data
**`music_schools_wikipedia.csv`**
- Source list of universities with columns:
  - University Name
  - URL
  - Other metadata fields

### 4. Progress Tracking
**`progress_tracker.txt`**
- Format:
  ```
  LAST_PROCESSED=123
  TOTAL_UNIVERSITIES=202
  ```
- Updated after each successful completion

## Output Structure

```
results/
├── batches/              # Individual CSV files per university
│   └── uni_XXX.csv       # Faculty data (University,Faculty Name,Title,Email,Phone,Profile URL,Notes)
├── url_logs/             # Permanent URL trails
│   └── uni_XXX_urls.txt  # List of all URLs visited for each school
└── no_trombone_found.csv # Schools with no trombone faculty

logs/
├── scraper_TIMESTAMP.log # Runtime logs
└── prompt_batch_XXX.txt  # Copy of each prompt sent

tmp/
└── uni_XXX_urls.txt      # Temporary URL logs (only during processing)

debug_screenshots/        # Screenshots of Claude Desktop for debugging
```

## Resume Logic

### How Resume Works
1. **During Processing**: Claude writes each visited URL to `tmp/uni_XXX_urls.txt`
2. **If Timeout Occurs**: URL log stays in `tmp/` for next run
3. **On Resume**: 
   - Script detects existing URL log in `tmp/`
   - Generates resume prompt with last visited URL
   - Claude continues from where it left off
4. **On Success**: URL log moves to `results/url_logs/` for permanent record

### Key Features
- **No Data Loss**: Results are always APPENDED, never overwritten
- **Complete Trail**: Every URL visited is logged
- **Automatic Resume**: System automatically detects and resumes incomplete universities
- **Context Management**: Each university runs in a fresh Claude instance

## Usage

### Start Scraping
```bash
./smart_automated_scraper_v2.sh
```

### View URL Logs
```bash
./view_url_logs.sh
```

### Check Progress
```bash
cat progress_tracker.txt
```

### Manual Resume Control
If needed, you can manually:
- Delete `tmp/uni_XXX_urls.txt` to force fresh start for a university
- Edit `progress_tracker.txt` to skip or retry universities

## Utility Scripts

### Optional Tools
- **`view_url_logs.sh`** - Display all URL trails from completed universities
- **`reset_incomplete.sh`** - Legacy script for clearing old incomplete markers (not needed in V2)

## Files in old/ Directory
These files are no longer used but kept for reference:
- `generate_single_prompt.py` - Original prompt generator without resume
- `generate_single_prompt_with_resume.py` - First attempt with complex JSON markers
- `smart_automated_scraper.sh` - Original version with infinite loop issue
- `generate_prompt.py` - Batch processing version
- `simple_prompt.py` - Early simple version

## Troubleshooting

### Common Issues

1. **Infinite Loop on Same University**
   - Check and remove `tmp/uni_XXX_urls.txt` for that university
   - Verify `progress_tracker.txt` has correct LAST_PROCESSED value

2. **Claude Not Responding**
   - Check `debug_screenshots/` for visual debugging
   - Ensure Claude Desktop app is installed and accessible
   - Try running `killall Claude` before restarting

3. **Missing Results**
   - Check `results/url_logs/uni_XXX_urls.txt` to see what was searched
   - Look in `results/no_trombone_found.csv` for schools with no faculty
   - Review `logs/scraper_TIMESTAMP.log` for errors

## Important Notes

- **One School at a Time**: System processes single universities to avoid context limits
- **3 Minute Timeout**: Each university has 3 minutes before timeout and resume
- **Automatic Progress**: Progress updates automatically on success
- **URL Tracking**: Every visited URL is logged for verification and resume

## Next Steps
Continue running `./smart_automated_scraper_v2.sh` until all 202 universities are processed. The system will automatically handle resumes and completions.