# LinkedIn Job Finder

A Python script that fetches LinkedIn job listings using your authenticated session cookie and saves the results to a CSV file.

---

## How It Works

The script uses your LinkedIn session cookie to make authenticated HTTP requests to LinkedIn's job search page. It parses job data from JSON blobs embedded in `<code>` tags (authenticated view) or falls back to fetching server-rendered HTML cards (unauthenticated view). It then optionally fetches applicant counts from each job's detail page and saves everything to a CSV file.

---

## Requirements

- Python 3.10+
- `requests`
- `beautifulsoup4`

Install dependencies:

```bash
pip install requests beautifulsoup4
```

---

## Setup

### 1. Get Your `li_at` Cookie

1. Log in to LinkedIn in your browser.
2. Open **DevTools** → **Application** → **Cookies** → `https://www.linkedin.com`
3. Copy the value of the `li_at` cookie.
4. Paste it into the `LI_AT` variable in the script.

### 2. Configure the Script

At the top of `LinkedIn_Job_Finder.py`, edit these variables:

```python
JOB_ROLE    = "Java Developer"        # Job title to search for
LOCATION    = "India"                 # Location to filter by
JOB_COUNT   = 200                     # Total number of jobs to collect
OUTPUT_FILE = "linkedin_jobs_bs4.csv" # Output CSV filename

LI_AT = "your_li_at_cookie_value_here"
```

---

## Usage

```bash
python LinkedIn_Job_Finder.py
```

When prompted, enter how many hours back you want job postings from:

```
Enter for how much hours you want job postings: 24
```

This filters jobs posted within the last N hours.

---

## Output

### Terminal Table

The script prints a formatted table to the terminal:

```
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#    Title                                  Company                    Location               Posted         Applicants
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
1    Java Developer                         Acme Corp                  Bengaluru, India       2025-06-05     45 applicants
...
Total: 200 jobs
```

### CSV File

Jobs are saved (appended) to `linkedin_jobs_bs4.csv` with the following columns:

| Column       | Description                        |
|--------------|------------------------------------|
| `title`      | Job title                          |
| `company`    | Company name                       |
| `location`   | Job location                       |
| `date_posted`| Date the job was posted (YYYY-MM-DD) |
| `applicants` | Number of applicants               |
| `job_url`    | Direct link to the LinkedIn job posting |

> If the CSV file already exists, new results are **appended** to it without duplicating the header row.

---
## How this Works

### Authenticated Mode (default)
When `LI_AT` is set, the session cookie is attached to all requests. LinkedIn returns pages with JSON data embedded in `<code>` tags. The script parses these JSON blobs to extract job details.

### Unauthenticated Fallback
If `LI_AT` is left empty (`""`), the script falls back to fetching publicly rendered HTML cards using CSS class selectors.

### Pagination
The script fetches pages in increments of 25 results, adding a random delay of **2–4 seconds** between page requests to avoid rate-limiting.

### Applicant Count Enrichment
After collecting all job listings, the script visits each job's detail page to extract the applicant count, with a random delay of **1–2.5 seconds** between requests.

---

## File Structure

```
LinkedIn_Job_Finder.py     # Main script
linkedin_jobs_bs4.csv      # Output file (generated after running)
```

---

## Key Functions

| Function              | Description                                                    |
|-----------------------|----------------------------------------------------------------|
| `make_session()`      | Creates an authenticated `requests.Session` with the `li_at` cookie |
| `fetch_page()`        | Fetches a page of LinkedIn job search results                  |
| `_parse_jobs_from_json()` | Extracts job data from embedded JSON in authenticated pages |
| `parse_jobs()`        | Parses HTML — tries JSON extraction first, falls back to HTML cards |
| `save_csv()`          | Appends collected jobs to the CSV output file                  |
| `print_table()`       | Prints a formatted summary table to the terminal               |
| `main()`              | Entry point — orchestrates the full program and save flow       |
