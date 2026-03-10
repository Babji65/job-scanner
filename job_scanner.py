import requests
import smtplib
import os
import json
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from jobspy import scrape_jobs

# ─────────────────────────────────────────────
#  CONFIGURATION — Edit these to match your needs
# ─────────────────────────────────────────────

JOB_KEYWORDS = [
    # --- Aerospace + Flight Software ---
    "flight software engineer intern",
    "flight software intern",
    "flight software co-op",
    "avionics software intern",
    "avionics software co-op",
    "embedded software aerospace intern",
    "spacecraft software intern",
    "spacecraft software co-op",

    # --- GNC / Simulation ---
    "guidance navigation control intern",
    "GNC software intern",
    "GNC engineer intern",
    "aerospace simulation intern",
    "simulation software engineer intern",
    "modeling and simulation intern",

    # --- Systems Engineering ---
    "systems engineer intern aerospace",
    "systems engineering intern",
    "systems engineering co-op",
    "aerospace systems engineer intern",
    "mission systems intern",

    # --- Defense / Military ---
    "defense software engineer intern",
    "defense systems engineer intern",
    "missile systems software intern",
    "C2 systems intern",
    "radar software intern",

    # --- Commercial Space ---
    "space systems software intern",
    "launch vehicle software intern",
    "satellite software intern",
    "satellite systems engineer intern",
    "propulsion software intern",

    # --- NASA / Government ---
    "NASA software engineering intern",
    "NASA systems engineer intern",
    "NASA intern computer science",
    "NASA co-op",
    "government aerospace intern",

    # --- Aviation / Aircraft ---
    "aircraft systems software intern",
    "avionics engineer intern",
    "flight controls software intern",
    "aircraft simulation intern",

    # --- Broad CS Net (aerospace companies) ---
    "software engineer intern",
    "software engineering co-op",
    "computer science intern",
    "backend engineer intern",
    "real-time systems intern",
    "autonomous systems intern",
    "robotics software intern",
]

# Only show jobs posted within this many days
MAX_AGE_DAYS = 2

# ─────────────────────────────────────────────
#  Secrets — set these in GitHub Actions Secrets
# ─────────────────────────────────────────────

EMAIL_SENDER   = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"].replace("\xa0", "").replace(" ", "").strip()
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]

ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# Register free at: https://developer.usajobs.gov/
USAJOBS_API_KEY    = os.environ.get("USAJOBS_API_KEY", "")
USAJOBS_USER_AGENT = os.environ.get("USAJOBS_USER_AGENT", "")  # must be your email

SEEN_JOBS_FILE = "seen_jobs.json"

# ─────────────────────────────────────────────
#  Load / Save seen jobs (prevents duplicates)
# ─────────────────────────────────────────────

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_jobs(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)

# ─────────────────────────────────────────────
#  Job Sources — Free APIs
# ─────────────────────────────────────────────

def search_remotive(keyword: str) -> list:
    """Remotive — free remote job API, no key required."""
    try:
        url = f"https://remotive.com/api/remote-jobs?search={keyword}&limit=20"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        jobs = []
        cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
        for job in resp.json().get("jobs", []):
            posted_str = job.get("publication_date", "")[:10]
            try:
                posted_dt = datetime.strptime(posted_str, "%Y-%m-%d")
            except ValueError:
                posted_dt = datetime.utcnow()
            if posted_dt >= cutoff:
                jobs.append({
                    "title":   job["title"],
                    "company": job["company_name"],
                    "url":     job["url"],
                    "posted":  posted_str,
                    "source":  "Remotive",
                    "tags":    ", ".join(job.get("tags", [])[:4]),
                })
        return jobs
    except Exception as e:
        print(f"[Remotive] Error: {e}")
        return []


def search_adzuna(keyword: str) -> list:
    """Adzuna — free tier, sign up at developer.adzuna.com."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
    try:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
            f"&what={requests.utils.quote(keyword)}"
            f"&max_days_old={MAX_AGE_DAYS}&results_per_page=20"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        jobs = []
        for job in resp.json().get("results", []):
            jobs.append({
                "title":   job.get("title", "N/A"),
                "company": job.get("company", {}).get("display_name", "N/A"),
                "url":     job.get("redirect_url", ""),
                "posted":  job.get("created", "")[:10],
                "source":  "Adzuna",
                "tags":    job.get("category", {}).get("label", ""),
            })
        return jobs
    except Exception as e:
        print(f"[Adzuna] Error: {e}")
        return []


def search_jobicy(keyword: str) -> list:
    """Jobicy — free remote job API, no key required."""
    try:
        url = f"https://jobicy.com/api/v2/remote-jobs?tag={requests.utils.quote(keyword)}&count=20"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        jobs = []
        cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
        for job in resp.json().get("jobs", []):
            posted_str = job.get("jobPubDate", "")[:10]
            try:
                posted_dt = datetime.strptime(posted_str, "%Y-%m-%d")
            except ValueError:
                posted_dt = datetime.utcnow()
            if posted_dt >= cutoff:
                jobs.append({
                    "title":   job.get("jobTitle", "N/A"),
                    "company": job.get("companyName", "N/A"),
                    "url":     job.get("url", ""),
                    "posted":  posted_str,
                    "source":  "Jobicy",
                    "tags":    job.get("jobType", ""),
                })
        return jobs
    except Exception as e:
        print(f"[Jobicy] Error: {e}")
        return []

# ─────────────────────────────────────────────
#  Job Sources — JobSpy (Indeed, LinkedIn, etc.)
# ─────────────────────────────────────────────

def search_jobspy(keyword: str) -> list:
    """Uses jobspy to scrape Indeed, LinkedIn, Glassdoor, ZipRecruiter.
    Install with: pip install jobspy
    """
    try:
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter"],
            search_term=keyword,
            location="United States",
            results_wanted=20,
            hours_old=MAX_AGE_DAYS * 24,
            country_indeed="USA",
            job_type="internship",    # filters for internships where supported
            is_remote=False,          # aerospace jobs are mostly on-site
        )
        jobs = []
        for _, row in df.iterrows():
            jobs.append({
                "title":   row.get("title", "N/A"),
                "company": row.get("company", "N/A"),
                "url":     row.get("job_url", ""),
                "posted":  str(row.get("date_posted", ""))[:10],
                "source":  str(row.get("site", "JobSpy")).capitalize(),
                "tags":    str(row.get("job_type", "")),
            })
        return jobs
    except Exception as e:
        print(f"[JobSpy] Error: {e}")
        return []

# ─────────────────────────────────────────────
#  Job Sources — USAJobs (NASA, DoD, Air Force)
# ─────────────────────────────────────────────

def search_usajobs(keyword: str) -> list:
    """USAJobs API — covers NASA, JPL, DoD, Air Force, etc.
    Register free at: https://developer.usajobs.gov/
    Set env vars: USAJOBS_API_KEY and USAJOBS_USER_AGENT (your email).
    """
    if not USAJOBS_API_KEY or not USAJOBS_USER_AGENT:
        print("[USAJobs] Skipping — missing USAJOBS_API_KEY or USAJOBS_USER_AGENT.")
        return []
    try:
        url = "https://data.usajobs.gov/api/search"
        headers = {
            "Host":              "data.usajobs.gov",
            "User-Agent":        USAJOBS_USER_AGENT,
            "Authorization-Key": USAJOBS_API_KEY,
        }
        params = {
            "Keyword":        keyword,
            "ResultsPerPage": 25,
            "WhoMayApply":    "all",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        jobs = []
        cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
        for item in resp.json().get("SearchResult", {}).get("SearchResultItems", []):
            pos = item.get("MatchedObjectDescriptor", {})
            posted_str = pos.get("PublicationStartDate", "")[:10]
            try:
                posted_dt = datetime.strptime(posted_str, "%Y-%m-%d")
            except ValueError:
                posted_dt = datetime.utcnow()
            if posted_dt >= cutoff:
                categories = pos.get("JobCategory", [])
                tag = categories[0].get("Name", "") if categories else ""
                jobs.append({
                    "title":   pos.get("PositionTitle", "N/A"),
                    "company": pos.get("OrganizationName", "N/A"),
                    "url":     pos.get("PositionURI", ""),
                    "posted":  posted_str,
                    "source":  "USAJobs",
                    "tags":    tag,
                })
        return jobs
    except Exception as e:
        print(f"[USAJobs] Error: {e}")
        return []

# ─────────────────────────────────────────────
#  Job Sources — Greenhouse (open JSON feeds)
#  SpaceX, Blue Origin, Northrop Grumman, L3Harris, Textron
# ─────────────────────────────────────────────

GREENHOUSE_BOARDS = {
    "SpaceX":           "spacex",
    "Blue Origin":      "blueorigin",
    "Northrop Grumman": "northropgrumman",
    "L3Harris":         "l3harris",
    "Textron":          "textron",
}

def search_greenhouse(keyword: str) -> list:
    """Scrapes Greenhouse job boards (open JSON — no auth required)."""
    jobs = []
    kw_lower = keyword.lower()
    for company, board_token in GREENHOUSE_BOARDS.items():
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            for job in resp.json().get("jobs", []):
                title = job.get("title", "")
                title_lower = title.lower()
                is_intern = any(t in title_lower for t in ["intern", "co-op", "coop", "student"])
                is_match  = any(w in title_lower for w in kw_lower.split())
                if is_intern and is_match:
                    updated = job.get("updated_at", "")[:10]
                    depts = job.get("departments", [])
                    tag = depts[0].get("name", "") if depts else ""
                    jobs.append({
                        "title":   title,
                        "company": company,
                        "url":     job.get("absolute_url", ""),
                        "posted":  updated,
                        "source":  f"Greenhouse",
                        "tags":    tag,
                    })
        except Exception as e:
            print(f"[Greenhouse:{company}] Error: {e}")
    return jobs

# ─────────────────────────────────────────────
#  Job Sources — Lever (open JSON feeds)
#  Anduril, Relativity Space, Rocket Lab, Joby, Archer
# ─────────────────────────────────────────────

LEVER_BOARDS = {
    "Anduril":          "anduril",
    "Relativity Space": "relativityspace",
    "Rocket Lab":       "rocketlab",
    "Joby Aviation":    "joby-aviation",
    "Archer Aviation":  "archeraviation",
}

def search_lever(keyword: str) -> list:
    """Scrapes Lever job boards (open JSON — no auth required)."""
    jobs = []
    kw_lower = keyword.lower()
    for company, slug in LEVER_BOARDS.items():
        try:
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            for job in resp.json():
                title = job.get("text", "")
                title_lower = title.lower()
                is_intern = any(t in title_lower for t in ["intern", "co-op", "coop", "student"])
                is_match  = any(w in title_lower for w in kw_lower.split())
                if is_intern and is_match:
                    created_ts = job.get("createdAt", 0) / 1000
                    posted_str = datetime.utcfromtimestamp(created_ts).strftime("%Y-%m-%d")
                    cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
                    if datetime.utcfromtimestamp(created_ts) >= cutoff:
                        jobs.append({
                            "title":   title,
                            "company": company,
                            "url":     job.get("hostedUrl", ""),
                            "posted":  posted_str,
                            "source":  "Lever",
                            "tags":    job.get("categories", {}).get("team", ""),
                        })
        except Exception as e:
            print(f"[Lever:{company}] Error: {e}")
    return jobs

# ─────────────────────────────────────────────
#  Job Sources — Workday (Lockheed, Boeing, Raytheon)
#  Note: Workday endpoint paths may shift — check each
#  company's careers page network tab if one stops working.
# ─────────────────────────────────────────────

WORKDAY_COMPANIES = {
    "Lockheed Martin": "https://lockheedmartin.wd5.myworkdayjobs.com/wday/cxs/lockheedmartin/LMCareers/jobs",
    "Boeing":          "https://boeing.wd1.myworkdayjobs.com/wday/cxs/boeing/EXTERNAL_CAREERS/jobs",
    "Raytheon":        "https://raytheon.wd5.myworkdayjobs.com/wday/cxs/raytheon/RTX/jobs",
}

def search_workday(keyword: str) -> list:
    """Hits Workday JSON endpoints for Lockheed Martin, Boeing, and Raytheon."""
    jobs = []
    payload = {
        "appliedFacets": {},
        "limit":         20,
        "offset":        0,
        "searchText":    keyword,
    }
    headers = {"Content-Type": "application/json"}
    for company, url in WORKDAY_COMPANIES.items():
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            base_url = url.split("/wday/")[0]
            for job in resp.json().get("jobPostings", []):
                title = job.get("title", "N/A")
                title_lower = title.lower()
                is_intern = any(t in title_lower for t in ["intern", "co-op", "coop", "student", "co op"])
                if is_intern:
                    jobs.append({
                        "title":   title,
                        "company": company,
                        "url":     base_url + job.get("externalPath", ""),
                        "posted":  job.get("postedOn", "")[:10],
                        "source":  "Workday",
                        "tags":    job.get("locationsText", ""),
                    })
        except Exception as e:
            print(f"[Workday:{company}] Error: {e}")
    return jobs

# ─────────────────────────────────────────────
#  Deduplication
# ─────────────────────────────────────────────

def deduplicate(jobs: list, seen_urls: set) -> list:
    unique = []
    seen_this_run = set()
    for job in jobs:
        key = job["url"]
        if key and key not in seen_urls and key not in seen_this_run:
            seen_this_run.add(key)
            unique.append(job)
    return unique

# ─────────────────────────────────────────────
#  Email
# ─────────────────────────────────────────────

def build_html(jobs: list) -> str:
    rows = ""
    for job in jobs:
        tags_html = f'<br><span style="font-size:11px;color:#94a3b8;">{job["tags"]}</span>' if job["tags"] else ""
        rows += f"""
        <tr>
          <td style="padding:12px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top;">
            <a href="{job['url']}" style="font-weight:600;color:#2563eb;text-decoration:none;font-size:14px;">{job['title']}</a><br>
            <span style="color:#475569;font-size:13px;">{job['company']}</span>
            {tags_html}
          </td>
          <td style="padding:12px 10px;border-bottom:1px solid #f1f5f9;color:#94a3b8;font-size:12px;white-space:nowrap;vertical-align:top;">{job['posted']}</td>
          <td style="padding:12px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top;">
            <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;">{job['source']}</span>
          </td>
        </tr>"""

    keywords_display = " &nbsp;·&nbsp; ".join(f"<code>{k}</code>" for k in JOB_KEYWORDS)
    date_str = datetime.utcnow().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:680px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);padding:28px 32px;">
      <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">🔍 Job Scan Results</h1>
      <p style="margin:6px 0 0;color:#bfdbfe;font-size:13px;">{date_str} &nbsp;·&nbsp; {len(jobs)} new listing{'s' if len(jobs) != 1 else ''} found</p>
    </div>

    <!-- Keywords -->
    <div style="padding:16px 32px;background:#eff6ff;border-bottom:1px solid #dbeafe;font-size:13px;color:#1e40af;">
      Searched for: {keywords_display}
    </div>

    <!-- Table -->
    <div style="padding:0 16px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:8px;">
        <thead>
          <tr style="background:#f8fafc;">
            <th style="padding:10px;text-align:left;font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;">Role / Company</th>
            <th style="padding:10px;text-align:left;font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;">Posted</th>
            <th style="padding:10px;text-align:left;font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid #e2e8f0;">Source</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;font-size:11px;color:#94a3b8;">
      Sent automatically by your GitHub Actions Job Scanner &nbsp;·&nbsp; Edit <code>job_scanner.py</code> to change keywords
    </div>
  </div>
</body>
</html>"""


def build_plain(jobs: list) -> str:
    lines = [f"Job Scan Results — {datetime.utcnow().strftime('%Y-%m-%d')}", "=" * 50, ""]
    for job in jobs:
        lines.append(f"{job['title']} @ {job['company']}")
        lines.append(f"  {job['url']}")
        lines.append(f"  Posted: {job['posted']}  |  Source: {job['source']}")
        lines.append("")
    return "\n".join(lines)


def send_email(jobs: list):
    if not jobs:
        print("No new jobs to report. Skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔍 Job Scan — {len(jobs)} new listing{'s' if len(jobs) != 1 else ''} ({datetime.utcnow().strftime('%b %d')})"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER

    msg.attach(MIMEText(build_plain(jobs), "plain"))
    msg.attach(MIMEText(build_html(jobs),  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

    print(f"✅ Email sent with {len(jobs)} jobs!")

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    print(f"Starting job scan — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    seen_urls = load_seen_jobs()

    all_jobs = []
    for keyword in JOB_KEYWORDS:
        print(f"  Searching: '{keyword}'")
        all_jobs += search_remotive(keyword)
        all_jobs += search_adzuna(keyword)
        all_jobs += search_jobicy(keyword)
        all_jobs += search_jobspy(keyword)       # Indeed, LinkedIn, Glassdoor, ZipRecruiter
        all_jobs += search_usajobs(keyword)      # NASA, DoD, Air Force, etc.
        all_jobs += search_greenhouse(keyword)   # SpaceX, Blue Origin, Northrop, L3Harris, Textron
        all_jobs += search_lever(keyword)        # Rocket Lab, Relativity, Joby, Anduril, Archer
        all_jobs += search_workday(keyword)      # Lockheed Martin, Boeing, Raytheon

    print(f"Raw results: {len(all_jobs)} jobs")
    new_jobs = deduplicate(all_jobs, seen_urls)
    print(f"New jobs (after dedup): {len(new_jobs)}")

    # Save all seen URLs so we don't re-send them tomorrow
    seen_urls.update(job["url"] for job in new_jobs)
    save_seen_jobs(seen_urls)

    send_email(new_jobs)

if __name__ == "__main__":
    main()
