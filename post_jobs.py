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
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    missing = []
    if not api_key:
        missing.append('HIREBASE_API_KEY')
    if not webhook_url:
        missing.append('DISCORD_WEBHOOK_URL')
    
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
    
    # Search payload for cybersecurity jobs
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
    
    try:
        logger.info(f"Fetching jobs from Hirebase API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response structures
        if isinstance(data, dict):
            jobs = data.get('jobs', data.get('results', data.get('data', [])))
        else:
            jobs = data
        
        logger.info(f"✅ Successfully fetched {len(jobs)} jobs")
        
        # Debug: Log the structure of the first job
        if jobs and len(jobs) > 0:
            logger.info(f"Sample job structure: {list(jobs[0].keys())}")
        
        return jobs
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching jobs: {e}")
        logger.error(f"Response: {e.response.text if e.response else 'No response'}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching jobs: {e}")
        return []


def format_job_embed(job: Dict) -> Dict:
    """
    Format a job posting as a Discord embed.
    
    Args:
        job: Job dictionary from Hirebase API
    
    Returns:
        Discord embed dictionary
    """
    # Try different possible field names from the API
    title = job.get('title') or job.get('job_title') or job.get('position') or 'Unknown Position'
    company = job.get('company_name') or job.get('company', {}).get('name') if isinstance(job.get('company'), dict) else job.get('company') or 'Unknown Company'
    location = job.get('location') or job.get('city') or job.get('location_type') or 'Not specified'
    description = job.get('description') or job.get('summary') or ''
    job_url = job.get('url') or job.get('link') or job.get('job_url') or ''
    salary = job.get('salary') or job.get('salary_range') or 'Not specified'
    
    # Truncate description if too long (Discord limit is 4096 chars)
    if len(description) > 300:
        description = description[:300] + "..."
    
    fields = [
        {
            "name": "🏢 Company",
            "value": str(company),
            "inline": True
        },
        {
            "name": "📍 Location",
            "value": str(location),
            "inline": True
        }
    ]
    
    # Add salary if available
    if salary and salary != 'Not specified':
        fields.append({
            "name": "💰 Salary",
            "value": str(salary),
            "inline": True
        })
    
    embed = {
        "title": title,
        "description": description or "No description available",
        "color": 3447003,  # Blue color
        "fields": fields,
        "footer": {
            "text": "Posted via Hirebase Job Bot"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Only add URL if it exists and is valid
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
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ Posted job {idx}/{len(jobs)}: {job.get('title', 'Unknown')}")
        
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