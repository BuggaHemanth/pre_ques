"""
Utility functions for the AI Maturity Assessment tool
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st


def load_config() -> Dict:
    """
    Load configuration from environment variables or Streamlit secrets

    Returns:
        Dict with API keys and configuration
    """
    config = {}

    # Try Streamlit secrets first (for deployment)
    try:
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            config['gemini_api_key'] = st.secrets.get('GEMINI_API_KEY', '')
            config['tavily_api_key'] = st.secrets.get('TAVILY_API_KEY', '')
            config['spreadsheet_id'] = st.secrets.get('SPREADSHEET_ID', '')

            # Google Sheets credentials
            if 'GOOGLE_SHEETS_CREDENTIALS' in st.secrets:
                config['google_credentials'] = dict(st.secrets['GOOGLE_SHEETS_CREDENTIALS'])
            else:
                config['google_credentials'] = None

            return config
    except Exception:
        # If secrets not available, fall through to .env
        pass

    # Fall back to environment variables (for local development)
    from dotenv import load_dotenv
    load_dotenv()

    config['gemini_api_key'] = os.getenv('GEMINI_API_KEY', '')
    config['tavily_api_key'] = os.getenv('TAVILY_API_KEY', '')
    config['spreadsheet_id'] = os.getenv('SPREADSHEET_ID', '')

    # Try to load Google credentials from file
    creds_file = 'google_credentials.json'
    if os.path.exists(creds_file):
        with open(creds_file, 'r') as f:
            config['google_credentials'] = json.load(f)
    else:
        config['google_credentials'] = None

    return config


def validate_config(config: Dict) -> tuple[bool, str]:
    """
    Validate that all required configuration is present

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = ['gemini_api_key', 'tavily_api_key']

    for key in required_keys:
        if not config.get(key):
            return False, f"Missing required configuration: {key}"

    # Check if at least one method of data storage is configured
    if not config.get('spreadsheet_id') and not config.get('google_credentials'):
        return False, "Google Sheets not configured. Data will not be saved."

    return True, ""


def save_to_google_sheets(data: Dict, config: Dict) -> tuple[bool, str]:
    """
    Save assessment data to Google Sheets

    Args:
        data: Assessment data to save
        config: Configuration with credentials

    Returns:
        Tuple of (success, message)
    """
    try:
        if not config.get('spreadsheet_id') or not config.get('google_credentials'):
            return False, "Google Sheets not configured"

        # Set up credentials
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        credentials = Credentials.from_service_account_info(
            config['google_credentials'],
            scopes=scopes
        )

        # Open spreadsheet
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(config['spreadsheet_id'])

        # Try to get or create worksheet named "webscrape"
        try:
            worksheet = spreadsheet.worksheet('webscrape')
        except gspread.exceptions.WorksheetNotFound:
            # Create worksheet with headers
            worksheet = spreadsheet.add_worksheet(
                title='webscrape',
                rows=1000,
                cols=15
            )
            headers = [
                'Timestamp',
                'Name',
                'Email',
                'Company Name',
                'Website URL',
                'Initial Score (Website)',
                'MCQ Score',
                'Final Score',
                'Maturity Tag',
                'Gaps Identified',
                'Queries Generated',
                'Tavily Links',
                'Scraped Pages Links',
                'Pages Crawled',
                'Summary'
            ]
            worksheet.append_row(headers)

        # Prepare row data
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data.get('name', ''),
            data.get('email', ''),
            data.get('company_name', ''),
            data.get('website_url', ''),
            data.get('initial_score', 0),
            data.get('mcq_score', 0),
            data.get('final_score', 0),
            data.get('maturity_tag', ''),
            data.get('gaps_identified', ''),
            data.get('queries_generated', ''),
            data.get('tavily_links', ''),
            data.get('scraped_links', ''),
            data.get('pages_crawled', 0),
            data.get('summary', '')
        ]

        # Append row
        worksheet.append_row(row)

        return True, "Data saved successfully"

    except Exception as e:
        return False, f"Error saving to Google Sheets: {str(e)}"


def get_maturity_badge(tag: str) -> str:
    """
    Get emoji badge for maturity tag

    Args:
        tag: Maturity tag (Novice, Explorer, Pacesetter, Trailblazer)

    Returns:
        Emoji representation
    """
    badges = {
        'Novice': '🌱',
        'Explorer': '🔍',
        'Pacesetter': '🚀',
        'Trailblazer': '⭐'
    }
    return badges.get(tag, '📊')


def get_tag_color(tag: str) -> str:
    """
    Get color for maturity tag

    Args:
        tag: Maturity tag

    Returns:
        Color name for Streamlit
    """
    colors = {
        'Novice': 'red',
        'Explorer': 'orange',
        'Pacesetter': 'blue',
        'Trailblazer': 'green'
    }
    return colors.get(tag, 'gray')


def format_score_display(score: int) -> str:
    """
    Format score for display with color coding

    Args:
        score: Score from 0-100

    Returns:
        Formatted string with markdown
    """
    if score <= 25:
        color = "🔴"
    elif score <= 50:
        color = "🟡"
    elif score <= 75:
        color = "🔵"
    else:
        color = "🟢"

    return f"{color} **{score}/100**"


def validate_email(email: str) -> bool:
    """
    Basic email validation

    Args:
        email: Email address to validate

    Returns:
        True if valid format
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate and normalize URL

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, normalized_url or error_message)
    """
    import re
    from urllib.parse import urlparse

    # Remove whitespace
    url = url.strip()

    # Add https:// if no protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Basic URL validation
    try:
        result = urlparse(url)
        if not result.netloc:
            return False, "Invalid URL format"

        # Check if it looks like a valid domain
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-_.]*\.[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, result.netloc.replace('www.', '')):
            return False, "Invalid domain name"

        return True, url

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def create_progress_callback():
    """
    Create a progress callback for long-running operations

    Returns:
        Function that can be called to update progress
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(progress: float, status: str):
        """Update progress bar and status text"""
        progress_bar.progress(min(progress, 1.0))
        status_text.text(status)

    return update_progress
