# 🔍 Automated Job Scanner

Scans multiple job boards daily and emails you new listings that match your keywords — powered by GitHub Actions. Completely free.

---

## What it does

- Runs automatically **Monday–Friday at 8am UTC**
- Searches **Remotive**, **Jobicy**, and optionally **Adzuna** for your keywords
- Filters to jobs posted in the last **2 days**
- Sends a formatted HTML email with job titles, companies, and direct links
- Remembers which jobs it already sent so you never get duplicates

---

## File Structure

```
your-repo/
├── .github/
│   └── workflows/
│       └── job_scanner.yml   ← GitHub Actions schedule & steps
├── job_scanner.py            ← Main script (edit keywords here)
├── seen_jobs.json            ← Auto-updated list of sent job URLs
└── README.md
```

---

## Setup Instructions

### Step 1 — Create a GitHub Repository

1. Go to [github.com](https://github.com) and click **New repository**
2. Name it something like `job-scanner`
3. Set it to **Private** (recommended)
4. Click **Create repository**

### Step 2 — Upload the files

Upload all three files to your repo:
- `job_scanner.py`
- `seen_jobs.json`
- `.github/workflows/job_scanner.yml`

You can do this via the GitHub web UI (**Add file → Upload files**) or with Git:

```bash
git clone https://github.com/YOUR_USERNAME/job-scanner.git
cd job-scanner
# copy in the files, then:
git add .
git commit -m "Initial commit"
git push
```

> **Important:** The `.github/` folder must be at the root of your repo. Make sure you're uploading the whole `.github/` folder, not just the yml file.

### Step 3 — Get a Gmail App Password

GitHub Actions needs to log in to Gmail to send your emails.  
You can't use your regular Gmail password — you need an **App Password**.

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** in the left sidebar
3. Under "How you sign in to Google", enable **2-Step Verification** if not already on
4. Search for **"App passwords"** in the search bar at the top
5. Select app: **Mail** → device: **Other** → type `Job Scanner` → click **Generate**
6. Copy the 16-character password shown (you won't see it again)

### Step 4 — Add GitHub Secrets

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each of these:

| Secret Name      | What to put                                      |
|------------------|--------------------------------------------------|
| `EMAIL_SENDER`   | Your Gmail address (e.g. `you@gmail.com`)        |
| `EMAIL_PASSWORD` | The 16-character App Password from Step 3        |
| `EMAIL_RECEIVER` | Where to send results (can be same Gmail address)|
| `ADZUNA_APP_ID`  | *(optional)* From developer.adzuna.com           |
| `ADZUNA_APP_KEY` | *(optional)* From developer.adzuna.com           |

The first three are **required**. Adzuna is optional but adds more listings.

### Step 5 (Optional) — Add Adzuna for More Results

Adzuna is a free job API that pulls from many boards including Indeed.

1. Sign up at [developer.adzuna.com](https://developer.adzuna.com)
2. Create an app to get your `App ID` and `App Key`
3. Add them as GitHub Secrets (see table above)

### Step 6 — Customize Your Keywords

Open `job_scanner.py` and edit the `JOB_KEYWORDS` list near the top:

```python
JOB_KEYWORDS = [
    "software engineer",
    "python developer",
    "backend engineer",
]
```

You can also change `MAX_AGE_DAYS` to get older listings (default is `2`).

### Step 7 — Test it manually

1. In your repo, go to the **Actions** tab
2. Click **🔍 Job Scanner** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Watch the logs — you should receive an email within ~30 seconds

---

## Changing the Schedule

Edit the `cron` line in `.github/workflows/job_scanner.yml`:

```yaml
- cron: '0 8 * * 1-5'   # 8am UTC, Mon–Fri
```

Use [crontab.guru](https://crontab.guru) to build a custom schedule.  
Note: GitHub Actions runs on UTC time.

| Schedule              | Cron expression   |
|-----------------------|-------------------|
| Every weekday 8am UTC | `0 8 * * 1-5`     |
| Every day 9am UTC     | `0 9 * * *`       |
| Twice daily (8am+5pm) | `0 8,17 * * 1-5`  |

---

## Troubleshooting

**No email received?**
- Check the Actions tab for error logs
- Make sure your App Password is correct (no spaces)
- Confirm 2FA is enabled on your Google account

**Getting "Permission denied" on git push?**
- Go to Settings → Actions → General → scroll to "Workflow permissions"
- Select **Read and write permissions** and save

**Jobs not appearing?**
- The APIs may have no results for your exact keywords — try broader terms
- Remotive and Jobicy focus on remote roles; Adzuna covers all job types
