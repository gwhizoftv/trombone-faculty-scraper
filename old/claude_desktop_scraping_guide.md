# Claude Desktop Interactive Faculty Scraping Guide

## Step 1: Test the MCP Servers
In Claude Desktop chat, type:
```
@playwright navigate to https://berklee.edu
```

## Step 2: Search for Faculty
Once on the site, use these steps:
1. Look for search functionality (search icon, button, or link)
2. Navigate to faculty directory or use search with "trombone"
3. Extract faculty information

## Example Commands for Claude Desktop:

### Navigate to website:
```
@playwright navigate to https://berklee.edu
```

### Look for search elements:
```
@playwright find all search buttons or links on the page
```

### Click search and enter term:
```
@playwright click the search button
@playwright type "trombone faculty" in the search field
@playwright press Enter
```

### Extract faculty information:
```
@playwright find all faculty profiles or links
@playwright click on first faculty link
@playwright extract text from the page
```

### Save results:
```
@filesystem write the faculty data to trombone_faculty.csv with columns: University, Name, Title, Email, URL
```

## Universities to Process:
1. Berklee College of Music - https://berklee.edu
2. Baldwin-Wallace Conservatory - http://www.bw.edu/academics/conservatory
3. Boston Conservatory at Berklee - https://bostonconservatory.berklee.edu
4. Juilliard School - https://www.juilliard.edu
5. Manhattan School of Music - https://www.msmnyc.edu

## Interactive Process:
1. Navigate to university website
2. Locate search or faculty directory
3. Search for "trombone" or navigate to brass/trombone faculty
4. Click on each faculty member
5. Extract: Name, Title, Email, Bio URL
6. Save to CSV file

## Expected Output Format:
```csv
University,Faculty Name,Title,Email,Profile URL
Berklee College of Music,John Doe,Professor of Trombone,jdoe@berklee.edu,https://berklee.edu/faculty/john-doe
```