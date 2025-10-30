import os
import sys
import json
import time
import requests
from typing import Optional, List, Dict
from datetime import datetime

# Channel keywords mapping
CHANNEL_KEYWORDS = {
    'data': ['data', 'analyst', 'analytics', 'scientist', 'engineer', 'bi', 'business intelligence', 'sql', 'tableau', 'power bi'],
    'operations': ['operations', 'ops', 'devops', 'sre', 'site reliability', 'infrastructure', 'systems', 'platform'],
    'security': ['security', 'infosec', 'cybersecurity', 'cyber', 'penetration', 'soc', 'grc', 'compliance', 'risk'],
    'development': ['developer', 'software engineer', 'frontend', 'backend', 'full stack', 'fullstack', 'mobile', 'web', 'programmer', 'coding'],
    'management': ['manager', 'director', 'lead', 'head of', 'chief', 'vp', 'vice president', 'executive', 'cto', 'cio'],
    'network': ['network', 'networking', 'cisco', 'routing', 'switching', 'firewall', 'vpn', 'wan', 'lan'],
    'supporthelp': ['support', 'help desk', 'helpdesk', 'customer service', 'technical support', 'it support', 'service desk']
}


def categorize_job(title: str, description: str, categories: Optional[List[str]] = None) -> Optional[str]:
    """Determine which channel a job belongs to"""
    search_text = f"{title} {description} {' '.join(categories or [])}".lower()
    
    for channel, keywords in CHANNEL_KEYWORDS.items():
        if any(keyword in search_text for keyword in keywords):
            return channel
    
    return None


def format_location(locations: Optional[List[Dict]]) -> str:
    """Format location string"""
    if not locations or len(locations) == 0:
        return 'Remote/Not specified'
    
    loc = locations[0]
    parts = [loc.get('city'), loc.get('region'), loc.get('country')]
    parts = [p for p in parts if p]
    return ', '.join(parts) if parts else 'Remote/Not specified'


def format_experience(yoe_range: Optional[Dict]) -> str:
    """Format experience level"""
    if not yoe_range:
        return 'Not specified'
    
    min_yoe = yoe_range.get('min')
    max_yoe = yoe_range.get('max')
    
    if min_yoe == max_yoe:
        return f"{min_yoe}+ years"
    return f"{min_yoe}-{max_yoe} years"


def format_salary(salary_range: Optional[Dict]) -> str:
    """Format salary"""
    if not salary_range:
        return 'Not disclosed'
    
    min_sal = salary_range.get('min')
    max_sal = salary_range.get('max')
    currency = salary_range.get('currency', 'USD')
    period = salary_range.get('period', 'year')
    
    if min_sal and max_sal:
        return f"${min_sal:,} - ${max_sal:,} {currency}/{period}"
    return 'Not disclosed'


def strip_html(text: str) -> str:
    """Simple HTML tag stripper"""
    import re
    return re.sub(r'<[^>]*>', '', text)


def format_job_embed(job: Dict) -> Dict:
    """Format job posting for Discord"""
    description = job.get('description', '')
    clean_description = strip_html(description)[:300] + '...' if description else 'No description available'
    
    return {
        'embeds': [{
            'title': job.get('job_title', 'Untitled Position'),
            'url': job.get('application_link'),
            'color': 0x5865F2,  # Discord blurple color
            'fields': [
                {
                    'name': '🏢 Company',
                    'value': job.get('company_name', 'Not specified'),
                    'inline': True
                },
                {
                    'name': '📍 Location',
                    'value': format_location(job.get('locations')),
                    'inline': True
                },
                {
                    'name': '💼 Type',
                    'value': job.get('job_type', 'Not specified'),
                    'inline': True
                },
                {
                    'name': '⏱️ Experience',
                    'value': format_experience(job.get('yoe_range')),
                    'inline': True
                },
                {
                    'name': '💰 Salary',
                    'value': format_salary(job.get('salary_range')),
                    'inline': True
                },
                {
                    'name': '🌐 Remote',
                    'value': job.get('location_type', 'Not specified'),
                    'inline': True
                }
            ],
            'description': clean_description,
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {
                'text': f"Posted: {job.get('date_posted', 'Unknown')} • Via Hirebase API"
            }
        }]
    }


def post_to_discord(webhook_url: str, job_data: Dict) -> None:
    """Post to Discord webhook"""
    response = requests.post(webhook_url, json=job_data)
    
    if response.status_code != 204:
        raise Exception(f"Discord API returned {response.status_code}")


def fetch_jobs(api_key: str) -> Dict:
    """Fetch jobs from Hirebase API"""
    if not api_key:
        raise Exception('HIREBASE_API_KEY not configured')
    
    print('API Key configured: Yes')
    
    url = 'https://api.hirebase.org/v2/jobs/search'
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    # Search payload - using broader search like the working code
    payload = {
        'job_titles': [
            'Security Engineer',
            'Security Analyst',
            'Cybersecurity Engineer',
            'Information Security Analyst',
            'SOC Analyst',
            'Penetration Tester',
            'Data Engineer',
            'Data Analyst',
            'Data Scientist',
            'Business Intelligence Analyst',
            'DevOps Engineer',
            'Site Reliability Engineer',
            'Software Engineer',
            'Software Developer',
            'Full Stack Developer',
            'Frontend Developer',
            'Backend Developer',
            'Engineering Manager',
            'Technical Lead',
            'Network Engineer',
            'Systems Administrator',
            'IT Support Specialist',
            'Help Desk Technician'
        ],
        'keywords': ['cybersecurity', 'security', 'data', 'software', 'developer', 'engineer'],
        'location_types': ['Remote', 'Hybrid'],
        'limit': 50
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f'Response status: {response.status_code}')
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        print(f'HTTP error: {e}')
        print(f'Response: {e.response.text if e.response else "No response"}')
        raise Exception(f'API returned {e.response.status_code}: {e.response.text}')
    except requests.exceptions.RequestException as e:
        print(f'Request error: {e}')
        raise


def main():
    try:
        print('Fetching jobs from Hirebase API...')
        api_key = os.environ.get('HIREBASE_API_KEY', '').strip()
        response = fetch_jobs(api_key)
        
        # Extract jobs array from response
        jobs = response.get('jobs', [])
        total_count = response.get('total_count', len(jobs))
        print(f'Found {len(jobs)} jobs (Total: {total_count})')
        
        if not jobs:
            print('No jobs found. Exiting.')
            return
        
        # Get webhooks from environment variables
        webhooks = {
            'data': os.environ.get('DISCORD_DATA_HOOK'),
            'operations': os.environ.get('DISCORD_OPS_HOOK'),
            'security': os.environ.get('DISCORD_SECURITY_HOOK'),
            'development': os.environ.get('DISCORD_DEV_HOOK'),
            'management': os.environ.get('DISCORD_MANAGEMENT_HOOK'),
            'network': os.environ.get('DISCORD_NETWORK_HOOK'),
            'supporthelp': os.environ.get('DISCORD_SUPPORTHELP_HOOK')
        }
        
        jobs_by_channel = {
            'data': [],
            'operations': [],
            'security': [],
            'development': [],
            'management': [],
            'network': [],
            'supporthelp': []
        }
        
        # Categorize jobs
        for job in jobs:
            channel = categorize_job(
                job.get('job_title', ''),
                job.get('description', ''),
                job.get('job_categories')
            )
            
            if channel and channel in jobs_by_channel:
                jobs_by_channel[channel].append(job)
            else:
                print(f"Job not categorized: {job.get('job_title')}")
        
        # Log categorization summary
        print('\nCategorization Summary:')
        for channel, channel_jobs in jobs_by_channel.items():
            print(f'  {channel}: {len(channel_jobs)} jobs')
        
        # Post jobs to respective channels (limit to top 5 per channel per day)
        total_posted = 0
        for channel, channel_jobs in jobs_by_channel.items():
            if not webhooks[channel]:
                print(f'\nNo webhook configured for {channel}, skipping...')
                continue
            
            if not channel_jobs:
                print(f'\nNo jobs for {channel}, skipping...')
                continue
            
            jobs_to_post = channel_jobs[:5]  # Limit to 5 jobs per channel
            print(f'\nPosting {len(jobs_to_post)} jobs to #{channel}...')
            
            for job in jobs_to_post:
                try:
                    embed = format_job_embed(job)
                    post_to_discord(webhooks[channel], embed)
                    total_posted += 1
                    print(f"  ✓ Posted: {job.get('job_title')}")
                    
                    # Rate limit: wait 1 second between posts
                    time.sleep(1)
                except Exception as error:
                    print(f"  ✗ Error posting \"{job.get('job_title')}\": {error}")
        
        print(f'\n✅ Job posting complete! Posted {total_posted} jobs total.')
    
    except Exception as error:
        print(f'❌ Error: {error}')
        sys.exit(1)


if __name__ == '__main__':
    main()