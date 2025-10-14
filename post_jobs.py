# post_jobs.py
import os
import requests
import datetime

HIREBASE_URL = "https://api.hirebase.org/v2/jobs/search"
HIREBASE_KEY = os.getenv("HIREBASE_API_KEY")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Adjust query to target cybersecurity roles
PAYLOAD = {
    "job_titles": [],                # optional: ["Security Engineer"]
    "keywords": ["cybersecurity"],   # main filter
    "location_types": ["Remote"]     # optional: ["Remote","Onsite","Hybrid"]
}

def fetch_jobs():
    headers = {
        "Content-Type": "application/json",
        "x-api-key": HIREBASE_KEY
    }
    r = requests.post(HIREBASE_URL, headers=headers, json=PAYLOAD, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])

def make_discord_payload(job):
    title = job.get("title") or "No title"
    company = job.get("company") or "Unknown"
    url = job.get("url") or job.get("apply_url") or ""
    location = job.get("location") or "N/A"
    posted_at = job.get("posted_at") or job.get("created_at") or ""

    embed = {
      "title": f"{title} — {company}",
      "url": url,
      "description": f"**Location:** {location}\n**Posted:** {posted_at}",
      "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    return {"embeds": [embed]}

def post_to_discord(payload):
    r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r

def main():
    if not HIREBASE_KEY or not WEBHOOK_URL:
        raise SystemExit("Missing HIREBASE_API_KEY or DISCORD_WEBHOOK_URL env vars.")

    jobs = fetch_jobs()
    if not jobs:
        print("No jobs returned.")
        return

    # Optionally limit how many to post per run to avoid spam / rate limits:
    for job in jobs[:5]:
        payload = make_discord_payload(job)
        try:
            post_to_discord(payload)
            print("Posted:", job.get("title"))
        except Exception as e:
            print("Failed to post:", e)

if __name__ == "__main__":
    main()
