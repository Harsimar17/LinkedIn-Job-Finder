"""
LinkedIn Job Scraper — BeautifulSoup Edition (Authenticated)
Scrapes LinkedIn job search using your logged-in session cookie.

HOW TO GET YOUR li_at COOKIE:
    1. Log in to LinkedIn in your browser.
    2. Open DevTools → Application → Cookies → https://www.linkedin.com
    3. Copy the value of the "li_at" cookie.
    4. Paste it into LI_AT below.

HOW TO USE:
    python linkedin_bs4_scraper.py

NOTE: Using your own account reduces rate-limiting significantly compared
to anonymous scraping, but LinkedIn's ToS still prohibits automated scraping.
Use responsibly and avoid running at high frequency.
"""

import csv
import os
import random
import time
from dataclasses import dataclass, fields, astuple
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────
#  CONFIGURE THESE
# ──────────────────────────────────────────────────
JOB_ROLE    = "Java Developer"   # e.g. Java Developer
LOCATION    = "India"       # e.g. "India
JOB_COUNT   = 200                    # total jobs to collect 
OUTPUT_FILE = "linkedin_jobs_bs4.csv"

# Paste your LinkedIn "li_at" session cookie value here.
# Leave as "" to fall back to unauthenticated (public) scraping.
LI_AT = "AQEDAU60xhADruwIAAABnplXqs8AAAGevWQuz1YAPraAq4irvZVFxytFMEtxSUuzJRHG9IOTjK6HdpWLY2nqRTODfICEdX06pheKyhiHof8qDPwDB7ihDFdilaLBYkvig5Oc68fxpZrHd0jsR1NhEYyI"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.linkedin.com/jobs/",
}

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    if LI_AT:
        session.cookies.set("li_at", LI_AT, domain=".linkedin.com")
        print("Using authenticated session (li_at cookie set).")
    else:
        print("No li_at cookie — falling back to unauthenticated scraping.")
    return session

SESSION = make_session()

@dataclass
class Job:
    title:       str
    company:     str
    location:    str
    date_posted: str
    applicants:  str
    job_url:     str


def build_params(keyword: str, location: str, start: int, seconds) -> dict:
    return {
        "keywords": keyword,
        "location": location,
        "f_TPR":seconds
    }


def fetch_page(start: int, seconds) -> str | None:
    params = build_params(JOB_ROLE, LOCATION, start, seconds)
    url = "https://www.linkedin.com/jobs/search/?" + urlencode(params)
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.text
        print(f"  [!] HTTP {resp.status_code} at start={start} — LinkedIn may be rate-limiting.")
        return None
    except requests.RequestException as e:
        print(f"  [!] Request error: {e}")
        return None

def _parse_jobs_from_json(soup: BeautifulSoup) -> list[Job]:
    """Extract jobs from the JSON blobs LinkedIn embeds in <code> tags (authenticated page)."""
    import json, re

    jobs: list[Job] = []
    for code_tag in soup.find_all("code"):
        raw = code_tag.get_text()
        if '"jobTitle"' not in raw and '"title"' not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        included = data.get("included", [])
        for item in included:
            item_type = item.get("$type", "")
            if "JobPosting" not in item_type and "jobPosting" not in item_type:
                continue
            maybe_title = item.get('title')
            
            if maybe_title:
                if type(maybe_title) is dict:
                    title = maybe_title.get("text").strip()
                else:
                    title = (item.get("title") or item.get("jobTitle") or "").strip()
            
            company = ""
            company_details = item.get("companyDetails") or {}
            if isinstance(company_details, dict):
                company = (
                    company_details.get("company", {}).get("name", "")
                    or company_details.get("companyName", "")
                    or ""
                ).strip()
            location = (item.get("formattedLocation") or item.get("location") or "").strip()
            date_posted = (item.get("listedAt") or item.get("originalListedAt") or "")
            if isinstance(date_posted, int):
                from datetime import datetime, timezone
                date_posted = datetime.fromtimestamp(date_posted / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            entity_urn = item.get("entityUrn", "")
            # Handle two URN formats:
            #   1. urn:li:jobPosting:4424984361
            #   2. urn:li:fsd_jobPostingCard:(4422677993,JOBS_SEARCH)
            job_id_match = re.search(r":(\d+)$", entity_urn) or re.search(r":\((\d+),", entity_urn)
            job_url = (
                f"https://www.linkedin.com/jobs/view/{job_id_match.group(1)}"
                if job_id_match else ""
            )

            if title:
                jobs.append(Job(title, company, location, str(date_posted), "N/A", job_url))

    return jobs


def parse_jobs(html: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")

    # Authenticated page: job data is embedded as JSON in <code> tags
    json_jobs = _parse_jobs_from_json(soup)
    if json_jobs:
        return json_jobs

    # Unauthenticated fallback: classic server-rendered HTML cards
    jobs: list[Job] = []
    for card in soup.find_all("li"):
        title_tag = card.find("h3", class_="base-search-card__title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        company_tag = card.find("h4", class_="base-search-card__subtitle")
        company = company_tag.get_text(strip=True) if company_tag else ""

        location_tag = card.find("span", class_="job-search-card__location")
        location = location_tag.get_text(strip=True) if location_tag else ""

        date_tag = card.find("time")
        date_posted = date_tag.get("datetime", "") if date_tag else ""

        link_tag = card.find("a", class_="base-card__full-link")
        job_url = link_tag["href"].split("?")[0] if link_tag and link_tag.get("href") else ""

        if title:
            jobs.append(Job(title, company, location, date_posted, "N/A", job_url))

    return jobs


def fetch_applicants(job_url: str) -> str:
    """Fetch the job detail page and extract the applicant count."""
    try:
        resp = SESSION.get(job_url, timeout=15)
        if resp.status_code != 200:
            return "N/A"
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("figcaption", class_="num-applicants__caption")
        print(tag.get_text(strip=True))
        return tag.get_text(strip=True) if tag else "N/A"
    except requests.RequestException:
        return "N/A"


def enrich_applicants(jobs: list[Job]) -> list[Job]:
    """Fetch applicant counts for all jobs from their detail pages."""
    print(f"\nFetching applicant counts for {len(jobs)} jobs…")
    for i, job in enumerate(jobs, 1):
        count = fetch_applicants(job.job_url)
        try:
            act_cont = count.split(" ")
            if int(act_cont[1]) < 100:
                print()
        except:
            print(count)
        
        job.applicants = count
        print(f"  [{i}/{len(jobs)}] {job.title[:40]:<42} → {count}")
        time.sleep(random.uniform(1.0, 2.5))
    return jobs

def save_csv(jobs: list[Job], filename: str):
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    headers = [f.name for f in fields(Job)]

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        for job in jobs:
            writer.writerow(astuple(job))

    print(f"\nSaved {len(jobs)} jobs to '{filename}'")


def print_table(jobs: list[Job]):
    line = "─" * 130
    print(f"\n{line}")
    print(f"{'#':<4} {'Title':<38} {'Company':<26} {'Location':<22} {'Posted':<14} {'Applicants'}")
    print(line)
    for i, j in enumerate(jobs, 1):
        print(
            f"{i:<4} {j.title[:36]:<38} {j.company[:24]:<26} "
            f"{j.location[:20]:<22} {j.date_posted:<14} {j.applicants}"
        )
    print(f"{line}\nTotal: {len(jobs)} jobs\n")


def main():
    print(f"Searching LinkedIn for: '{JOB_ROLE}' in '{LOCATION}'")
    print(f"Target: {JOB_COUNT} jobs\n")

    all_jobs: list[Job] = []
    start = 0
    try:
        hours = float(input("Enter for how much hours you want job postings: "))
        if hours < 0:
            raise ValueError("Hours cannot be negative.")

        seconds = int(hours * 3600)
        print(f"{hours} hours = {seconds} seconds")

    except ValueError as e:
        print(f"Invalid input: {e}")
    while len(all_jobs) < JOB_COUNT:
        print(f"  Fetching page at offset {start}…", end=" ", flush=True)
        html = fetch_page(start, seconds)

        if not html:
            print("stopping early due to error.")
            break

        page_jobs = parse_jobs(html)
        if not page_jobs:
            print("no jobs found — end of results or blocked.")
            break

        print(f"{len(page_jobs)} jobs found.")
        all_jobs.extend(page_jobs)
        start += 25

        # Polite delay to avoid rate-limiting
        time.sleep(random.uniform(2.0, 4.0))

    all_jobs = all_jobs[:JOB_COUNT]
    if all_jobs:
        print_table(all_jobs)
        save_csv( all_jobs, OUTPUT_FILE)
    else:
        print("No jobs found. Try different keywords or check your internet connection.")

if __name__ == "__main__":
    main()
