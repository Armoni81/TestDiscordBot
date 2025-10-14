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
    # Try different potential endpoints
    endpoints_to_try = [
        "https://api.hirebase.org/jobs/search",
        "https://api.hirebase.org/v1/jobs/search",
        "https://www.hirebase.org/api/jobs/search",
    ]
    
    params = {
        "query": "cybersecurity",
        "limit": 10
    }
    
    for url in endpoints_to_try:
        try:
            logger.info(f"Trying endpoint: {url}")
            
            # Try with X-API-Key header
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                jobs = response.json()
                logger.info(f"✅ Successfully fetched {len(jobs)} jobs from {url}")
                return jobs
            elif response.status_code == 401:
                # Try Bearer token instead
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    jobs = response.json()
                    logger.info(f"✅ Successfully fetched {len(jobs)} jobs from {url}")
                    return jobs
            
            logger.warning(f"Endpoint {url} returned status {response.status_code}: {response.text[:200]}")
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to {url}: {e}")
            continue
    
    logger.error("All API endpoints failed. Please verify:")
    logger.error("1. Your HIREBASE_API_KEY is valid")
    logger.error("2. The API key has proper permissions") 
    logger.error("3. You've requested API access from hirebase.org")
    return []


def format_job_embed(job: Dict) -> Dict:
    """
    Format a job posting as a Discord embed.
    
    Args:
        job: Job dictionary from Hirebase API
    
    Returns:
        Discord embed dictionary
    """
    # Adjust field names based on actual Hirebase API response
    title = job.get('title', 'Unknown Position')
    company = job.get('company', {}).get('name', 'Unknown Company')
    location = job.get('location', 'Remote')
    description = job.get('description', '')
    job_url = job.get('url', '')
    
    # Truncate description if too long (Discord limit is 4096 chars)
    if len(description) > 300:
        description = description[:300] + "..."
    
    embed = {
        "title": title,
        "description": description,
        "url": job_url,
        "color": 3447003,  # Blue color
        "fields": [
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
        ],
        "footer": {
            "text": "Posted via Hirebase Job Bot"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
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