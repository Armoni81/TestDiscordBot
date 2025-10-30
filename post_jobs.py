import os
import requests
import json

# Get API key
api_key = os.getenv('HIREBASE_API_KEY', '').strip()

print(f"API Key configured: {bool(api_key)}")
print(f"API Key length: {len(api_key)}")

# EXACT request format from working code
url = "https://api.hirebase.org/v2/jobs/search"
headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

payload = {
    "job_titles": [
        "Security Engineer",
        "Security Analyst", 
        "Cybersecurity Engineer",
        "Information Security Analyst",
        "SOC Analyst",
        "Penetration Tester"
    ],
    "keywords": ["cybersecurity", "security"],
    "location_types": ["Remote", "Hybrid"]
}

print("\n--- Request Details ---")
print(f"URL: {url}")
print(f"Headers: {json.dumps({**headers, 'x-api-key': '***'}, indent=2)}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"\n--- Response ---")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text[:500]}")
    
    if response.status_code == 200:
        data = response.json()
        jobs = data.get('jobs', [])
        print(f"\n✅ SUCCESS! Got {len(jobs)} jobs")
    else:
        print(f"\n❌ FAILED with status {response.status_code}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")