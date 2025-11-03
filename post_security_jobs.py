import os
import sys
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_poster.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid"""
    pass


def validate_environment() -> tuple[str, str]:
    """
    Validate that required environment variables are set.
    
    Returns:
        Tuple of (api_key, webhook_url)
    
    Raises:
        ConfigError: If required environment variables are missing
    """
    api_key = os.getenv('HIREBASE_API_KEY')
    webhook_url = os.getenv('DISCORD_SECURITY_HOOK')
    
    missing = []
    if not api_key:
        missing.append('HIREBASE_API_KEY')
    if not webhook_url:
        missing.append('DISCORD_SECURITY_HOOK')
    
    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        logger.error("Please set these in your GitHub repository secrets")
        raise ConfigError(error_msg)
    
    logger.info("✅ Environment variables validated successfully")
    return api_key, webhook_url


def fetch_cybersecurity_jobs(api_key: str) -> List[Dict]:
    """
    Fetch cybersecurity jobs from Hirebase API.
    
    Args:
        api_key: Hirebase API key
    
    Returns:
        List of job dictionaries
    """
    url = "https://api.hirebase.org/v2/jobs/search"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
  "job_titles": [
    "Cybersecurity Engineer",
    "Information Security Analyst",
    "Security Engineer",
    "Security Analyst",
    "Security Operations Center (SOC) Analyst",
    "Network Security Engineer",
    "Application Security Engineer",
    "Cloud Security Engineer",
    "Security Architect",
    "Penetration Tester",
    "Ethical Hacker",
    "Incident Response Analyst",
    "Security Compliance Analyst",
    "Vulnerability Management Engineer",
    "Information Assurance Engineer",
    "Identity and Access Management (IAM) Engineer",
    "Threat Intelligence Analyst",
    "Risk Analyst",
    "Security Consultant",
    "IT Security Specialist"
  ],
  "keywords": [
    "cybersecurity",
    "infosec",
    "security engineer",
    "soc",
    "network security",
    "application security",
    "cloud security",
    "penetration testing",
    "vulnerability management",
    "incident response",
    "risk assessment",
    "identity access management",
    "siem",
    "firewall",
    "threat detection",
    "compliance",
    "nist",
    "iso 27001",
    "splunk",
    "Atlanta"
  ],
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
        logger.info(f"Fetching jobs from Hirebase API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract jobs from the response
        jobs = data.get('jobs', [])
		# HERE Get a random length of job so the same jobs wont be posted  🚨🚨
		# logger.info(jobs, 'here')
        total_count = data.get('total_count', len(jobs))
        
        logger.info(f"✅ Successfully fetched {len(jobs)} jobs (total available: {total_count})")
        
        return jobs
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching jobs: {e}")
        logger.error(f"Response: {e.response.text if e.response else 'No response'}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching jobs: {e}")
        return []


def format_job_embed(job: Dict) -> Optional[Dict]:
    """
    Format a job posting as a Discord embed.
    
    Args:
        job: Job dictionary from Hirebase API
    
    Returns:
        Discord embed dictionary or None if job format is invalid
    """
    if not isinstance(job, dict):
        logger.warning(f"Unexpected job type: {type(job)}")
        return None
    
    # Extract fields from Hirebase API response
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
    
    # Get description (truncate if too long)
    description = job.get('requirements_summary', '') or job.get('description', '')
    if len(description) > 400:
        description = description[:400] + "..."
    
    # Get application link
    job_url = job.get('application_link', '')
    
    # Build fields
    fields = [
        {
            "name": "🏢 Company",
            "value": company,
            "inline": True
        },
        {
            "name": "📍 Location",
            "value": location,
            "inline": True
        }
    ]
    
    # Add job type and location type
    if job_type:
        fields.append({
            "name": "💼 Type",
            "value": f"{job_type}" + (f" • {location_type}" if location_type else ""),
            "inline": True
        })
    
    # Add salary if available
    salary_range = job.get('salary_range')
    if salary_range and isinstance(salary_range, dict):
        salary_min = salary_range.get('min', 0)
        salary_max = salary_range.get('max', 0)
        currency = salary_range.get('currency', 'USD')
        if salary_min and salary_max:
            fields.append({
                "name": "💰 Salary",
                "value": f"${salary_min:,} - ${salary_max:,} {currency}",
                "inline": True
            })
    
    # Add experience range if available
    yoe_range = job.get('yoe_range')
    if yoe_range and isinstance(yoe_range, dict):
        yoe_min = yoe_range.get('min', 0)
        yoe_max = yoe_range.get('max', 0)
        if yoe_min or yoe_max:
            fields.append({
                "name": "📅 Experience",
                "value": f"{yoe_min}+ years" if yoe_min == yoe_max else f"{yoe_min}-{yoe_max} years",
                "inline": True
            })
    
    # Add key skills
    skills = job.get('skills', [])
    if skills and isinstance(skills, list):
        top_skills = ', '.join(skills[:5])
        fields.append({
            "name": "🔧 Key Skills",
            "value": top_skills,
            "inline": False
        })
    
    embed = {
        "title": title,
        "description": description or "Click below to view full job details",
        "color": 5814783,  # Purple-blue color
        "fields": fields,
        "footer": {
            "text": f"Posted {job.get('date_posted', 'recently')} via Hirebase"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add URL if available
    if job_url and job_url.startswith('http'):
        embed["url"] = job_url
    
    return embed


def post_to_discord(webhook_url: str, jobs: List[Dict]) -> bool:
    """
    Post job listings to Discord channel.
    
    Args:
        webhook_url: Discord webhook URL
        jobs: List of job dictionaries
    
    Returns:
        True if successful, False otherwise
    """
    if not jobs:
        logger.warning("No jobs to post")
        return False
    
    try:
        # Post summary message
        summary_payload = {
            "content": f"🔒 **Daily Cybersecurity Jobs Update** - {len(jobs)} new positions",
        }
        
        response = requests.post(webhook_url, json=summary_payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Posted summary message")
        
        # Post individual jobs as embeds
        for idx, job in enumerate(jobs, 1):
            embed = format_job_embed(job)
            
            if embed is None:
                logger.warning(f"Skipping job {idx} - invalid format")
                continue
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Posted job {idx}/{len(jobs)}: {embed.get('title', 'Unknown')}")
        
        return True
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error posting to Discord: {e}")
        logger.error(f"Response: {e.response.text if e.response else 'No response'}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error posting to Discord: {e}")
        return False


def send_test_message(webhook_url: str) -> bool:
    """
    Send a test message to Discord to verify webhook.
    
    Args:
        webhook_url: Discord webhook URL
    
    Returns:
        True if successful, False otherwise
    """
    test_payload = {
        "content": "🧪 Test message from Cybersecurity Job Bot - Setup successful!",
        "embeds": [{
            "title": "Bot Configuration Test",
            "description": "If you're seeing this, the bot is configured correctly!",
            "color": 5763719,  # Green
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Test message sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send test message: {e}")
        return False


def main():
    """Main execution function"""
    logger.info("=" * 50)
    logger.info("Starting Cybersecurity Job Poster Bot")
    logger.info("=" * 50)
    
    try:
        # Validate environment
        api_key, webhook_url = validate_environment()
        
        # Check if running in test mode
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
        if test_mode:
            logger.info("🧪 Running in TEST MODE - sending test message only")
            success = send_test_message(webhook_url)
            sys.exit(0 if success else 1)
        
        # Fetch jobs
        jobs = fetch_cybersecurity_jobs(api_key)
        
        if not jobs:
            logger.warning("No jobs found to post")
            sys.exit(0)
        
        # Post to Discord
        success = post_to_discord(webhook_url, jobs)
        
        if success:
            logger.info("✅ Job posting completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Job posting failed")
            sys.exit(1)
            
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()