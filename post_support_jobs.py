import os
import sys
import requests
from datetime import datetime
from typing import List, Dict, Optional
import re

def fetch_security_jobs(api_key: str) -> List[Dict]:
    """Fetch security jobs from Hirebase API"""
    if not api_key:
        raise Exception('HIREBASE_API_KEY not configured')
    
    print('Fetching security jobs from Hirebase API...')
    
    url = 'https://api.hirebase.org/v2/jobs/search'
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }

    # FIXED: Proper indentation
    payload = {
        "job_titles": [
            "IT Support Specialist",
            "Technical Support Engineer",
            "Help Desk Technician",
            "Service Desk Analyst",
            "Application Support Engineer",
            "Desktop Support Technician",
            "IT Operations Support",
            "Systems Support Engineer",
            "Network Support Technician",
            "NOC Technician",
            "IT Support Engineer",
            "Cloud Support Associate",
            "Technical Support Specialist",
            "Production Support Engineer"
        ],
        "keywords": ["cybersecurity", "security", "infosec", "Atlanta"],
        "location_types": ["Remote", "Hybrid"],
        "geo_locations": [
            {
                "city": "Atlanta",
                "region": "Georgia",
                "country": "United States"
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f'Response status: {response.status_code}')
        response.raise_for_status()
        
        data = response.json()
        jobs = data.get('jobs', [])
        total_count = data.get('total_count', len(jobs))
        
        print(f'✅ Successfully fetched {len(jobs)} jobs (total available: {total_count})')
        return jobs
        
    except requests.exceptions.HTTPError as e:
        print(f'HTTP error fetching jobs: {e}')
        print(f'Response: {e.response.text if e.response else "No response"}')
        return []
    except requests.exceptions.RequestException as e:
        print(f'Error fetching jobs: {e}')
        return []

def strip_html(text: str) -> str:
    """Strip HTML tags from text"""
    return re.sub(r'<[^>]*>', '', text)


def format_job_embed(job: Dict) -> Optional[Dict]:
    """Format a job posting as a Discord embed"""
    if not isinstance(job, dict):
        print(f'Unexpected job type: {type(job)}')
        return None
    
    title = job.get('job_title', 'Unknown Position')
    company = job.get('company_name', 'Unknown Company')
    location_type = job.get('location_type', '')
    job_type = job.get('job_type', '')
    
    # Handle locations array
    locations = job.get('locations', [])
    if locations and len(locations) > 0:
        loc = locations[0]
        city = loc.get('city', '')
        country = loc.get('country', '')
        location = f"{city}, {country}" if city and country else (city or country or location_type)
    else:
        location = location_type or 'Not specified'
    
    # Get description
    description = job.get('requirements_summary', '') or job.get('description', '')
    if description:
        description = strip_html(description)
        if len(description) > 400:
            description = description[:400] + '...'
    else:
        description = 'Click below to view full job details'
    
    # Get application link
    job_url = job.get('application_link', '')
    
    # Build fields
    fields = [
        {
            'name': '🏢 Company',
            'value': company,
            'inline': True
        },
        {
            'name': '📍 Location',
            'value': location,
            'inline': True
        }
    ]
    
    # Add job type
    if job_type:
        fields.append({
            'name': '💼 Type',
            'value': f"{job_type}" + (f" • {location_type}" if location_type else ""),
            'inline': True
        })
    
    # Add salary if available
    salary_range = job.get('salary_range')
    if salary_range and isinstance(salary_range, dict):
        salary_min = salary_range.get('min', 0)
        salary_max = salary_range.get('max', 0)
        currency = salary_range.get('currency', 'USD')
        if salary_min and salary_max:
            fields.append({
                'name': '💰 Salary',
                'value': f"${salary_min:,} - ${salary_max:,} {currency}",
                'inline': True
            })
    
    # Add experience range
    yoe_range = job.get('yoe_range')
    if yoe_range and isinstance(yoe_range, dict):
        yoe_min = yoe_range.get('min', 0)
        yoe_max = yoe_range.get('max', 0)
        if yoe_min or yoe_max:
            fields.append({
                'name': '📅 Experience',
                'value': f"{yoe_min}+ years" if yoe_min == yoe_max else f"{yoe_min}-{yoe_max} years",
                'inline': True
            })
    
    # Add key skills
    skills = job.get('skills', [])
    if skills and isinstance(skills, list):
        top_skills = ', '.join(skills[:5])
        fields.append({
            'name': '🔧 Key Skills',
            'value': top_skills,
            'inline': False
        })
    
    embed = {
        'title': title,
        'description': description,
        'color': 0xE74C3C,  # Red color for security
        'fields': fields,
        'footer': {
            'text': f"Posted {job.get('date_posted', 'recently')} via Hirebase"
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Add URL if available
    if job_url and job_url.startswith('http'):
        embed['url'] = job_url
    
    return embed


def post_to_discord(webhook_url: str, jobs: List[Dict]) -> bool:
    """Post job listings to Discord channel"""
    if not jobs:
        print('No jobs to post')
        return False
    
    try:
        # Post summary message
        summary_payload = {
            'content': f'🔒 **Daily Security Jobs Update** - {len(jobs)} new positions',
        }
        
        response = requests.post(webhook_url, json=summary_payload, timeout=10)
        response.raise_for_status()
        print('✅ Posted summary message')
        
        # Post individual jobs as embeds (limit to 10 to avoid spam)
        for idx, job in enumerate(jobs[:10], 1):
            embed = format_job_embed(job)
            
            if embed is None:
                print(f'Skipping job {idx} - invalid format')
                continue
            
            payload = {
                'embeds': [embed]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ Posted job {idx}/{min(len(jobs), 10)}: {embed.get('title', 'Unknown')}")
        
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f'HTTP error posting to Discord: {e}')
        print(f'Response: {e.response.text if e.response else "No response"}')
        return False
    except requests.exceptions.RequestException as e:
        print(f'Error posting to Discord: {e}')
        return False


def main():
    """Main execution function"""
    print('=' * 50)
    print('Starting Cybersecurity Job Poster Bot')
    print('=' * 50)
    
    try:
        # Get environment variables
        api_key = os.getenv('HIREBASE_API_KEY', '').strip()
        webhook_url = os.getenv('DISCORD_SECURITY_HOOK', '').strip()
        
        if not api_key:
            raise Exception('HIREBASE_API_KEY not configured')
        
        if not webhook_url:
            raise Exception('DISCORD_SECURITY_HOOK not configured')
        
        print('✅ Environment variables validated')
        
        # Fetch jobs
        jobs = fetch_security_jobs(api_key)
        
        if not jobs:
            print('No jobs found to post')
            sys.exit(0)
        
        # Post to Discord
        success = post_to_discord(webhook_url, jobs)
        
        if success:
            print('✅ Job posting completed successfully')
            sys.exit(0)
        else:
            print('❌ Job posting failed')
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()