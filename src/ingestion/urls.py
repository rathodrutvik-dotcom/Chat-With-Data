"""Handles URL ingestion, validation, web scraping, and content storage."""

import os
import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import gradio as gr

from config.settings import (
    DATA_DIR, 
    IST, 
    URL_TIMEOUT, 
    ENABLE_CRAWLING, 
    MAX_PAGES_PER_URL, 
    USER_AGENT
)

logger = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """Validate URL format and reachability.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid and reachable, False otherwise
    """
    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Check if URL is reachable
    try:
        response = requests.head(url, timeout=URL_TIMEOUT, allow_redirects=True,
                                headers={"User-Agent": USER_AGENT})
        return response.status_code < 400
    except (requests.RequestException, Exception) as e:
        logger.warning(f"URL validation failed for {url}: {str(e)}")
        return False


def extract_domain(url: str) -> str:
    """Extract clean domain name from URL.
    
    Args:
        url: Full URL string
        
    Returns:
        Clean domain name (e.g., "docs.python.org")
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def extract_path_name_from_url(url: str) -> str:
    """Extract clean path name from URL for display and filename.
    
    Args:
        url: Full URL string
        
    Returns:
        Clean path name (e.g., "about-us", "services-pricing", "home")
    """
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Handle root URL
    if not path:
        return "home"
    
    # Remove query parameters and fragments
    path = path.split('?')[0].split('#')[0]
    
    # Replace slashes with hyphens, limit to 3 segments
    segments = path.split('/')
    if len(segments) > 3:
        segments = segments[:3]
    
    # Join with hyphens and clean up
    clean_name = '-'.join(segments)
    
    # Remove file extensions (.html, .php, etc.)
    clean_name = re.sub(r'\.(html?|php|aspx?|jsp)$', '', clean_name, flags=re.IGNORECASE)
    
    # Replace special characters with hyphens
    clean_name = re.sub(r'[^a-zA-Z0-9-]+', '-', clean_name)
    
    # Remove multiple consecutive hyphens
    clean_name = re.sub(r'-+', '-', clean_name).strip('-')
    
    # Limit length
    if len(clean_name) > 50:
        clean_name = clean_name[:50].rsplit('-', 1)[0]
    
    return clean_name or "page"


def get_page_title(soup: BeautifulSoup, url: str) -> str:
    """Extract page title from HTML.
    
    Args:
        soup: BeautifulSoup object
        url: Page URL (fallback if no title found)
        
    Returns:
        Page title string
    """
    # Try to get title tag
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        if title:
            return title
    
    # Try h1 tag as fallback
    h1 = soup.find('h1')
    if h1 and h1.get_text():
        return h1.get_text().strip()
    
    # Use URL path as last resort
    parsed = urlparse(url)
    path = parsed.path.strip('/').split('/')[-1] or 'index'
    return path.replace('-', ' ').replace('_', ' ').title()


def extract_menu_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract menu/navigation links from HTML.
    
    Args:
        soup: BeautifulSoup object
        base_url: Base URL for resolving relative links
        
    Returns:
        List of absolute URLs found in navigation elements
    """
    links = set()
    base_domain = extract_domain(base_url)
    
    # Look for navigation elements (nav, menu, header)
    nav_elements = soup.find_all(['nav', 'header', 'aside'])
    nav_elements += soup.find_all(class_=re.compile(r'menu|nav|navigation|sidebar', re.I))
    nav_elements += soup.find_all(id=re.compile(r'menu|nav|navigation|sidebar', re.I))
    
    # Also check main content for key links (but limit to avoid scraping entire site)
    main_content = soup.find(['main', 'article'])
    if main_content:
        nav_elements.append(main_content)
    
    for element in nav_elements:
        for link in element.find_all('a', href=True):
            href = link['href']
            # Skip anchors, javascript, and mailto links
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Only include links from same domain
            if extract_domain(absolute_url) == base_domain:
                # Remove URL fragments
                absolute_url = absolute_url.split('#')[0]
                links.add(absolute_url)
    
    return list(links)


def extract_text_content(soup: BeautifulSoup) -> str:
    """Extract clean text content from HTML, including footer content.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Cleaned text content with footer information
    """
    # Remove script and style elements
    for element in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
        element.decompose()
    
    # Extract footer separately FIRST (before main content extraction)
    footer = soup.find('footer')
    footer_text = ""
    if footer:
        footer_text = footer.get_text(separator='\n', strip=True)
        # Remove footer from soup temporarily to avoid duplication
        footer.extract()  # Use extract() instead of decompose()
    
    # Extract main content
    main_content = None
    for tag in ['main', 'article', '[role="main"]']:
        main_content = soup.select_one(tag)
        if main_content:
            break
    
    # If no main content found, use body
    if not main_content:
        main_content = soup.find('body')
    
    if not main_content:
        main_content = soup
    
    # Extract text from main content
    text = main_content.get_text(separator='\n', strip=True)
    
    # Append footer at the end with clear separator
    if footer_text:
        text += "\n\n--- Footer & Contact Information ---\n" + footer_text
    
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


def fetch_url_content(url: str) -> Dict[str, any]:
    """Fetch and parse content from a single URL.
    
    Args:
        url: URL to fetch
        
    Returns:
        Dictionary with keys: url, title, content, domain, links, success, error
    """
    result = {
        'url': url,
        'title': '',
        'content': '',
        'domain': extract_domain(url),
        'links': [],
        'success': False,
        'error': None
    }
    
    try:
        # Fetch URL with timeout
        response = requests.get(
            url, 
            timeout=URL_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract metadata
        result['title'] = get_page_title(soup, url)
        result['content'] = extract_text_content(soup)
        result['links'] = extract_menu_links(soup, url) if ENABLE_CRAWLING else []
        result['success'] = True
        
        logger.info(f"Successfully fetched: {url} (Title: {result['title']}, "
                   f"{len(result['content'])} chars, {len(result['links'])} links)")
        
    except requests.Timeout:
        result['error'] = "Request timed out"
        logger.error(f"Timeout fetching {url}")
    except requests.RequestException as e:
        result['error'] = f"Request failed: {str(e)}"
        logger.error(f"Error fetching {url}: {str(e)}")
    except Exception as e:
        result['error'] = f"Parsing failed: {str(e)}"
        logger.error(f"Error parsing {url}: {str(e)}")
    
    return result


def crawl_website(root_url: str, max_pages: int = MAX_PAGES_PER_URL) -> List[Dict[str, any]]:
    """Fetch content from URL(s). Behavior controlled by ENABLE_CRAWLING config.
    
    Args:
        root_url: Starting URL
        max_pages: Maximum total pages to crawl (only used if ENABLE_CRAWLING=True)
        
    Returns:
        List of fetched page data dictionaries
    """
    
    if not ENABLE_CRAWLING:
        # Single page mode: fetch only the given URL
        logger.info(f"Fetching single page from: {root_url} (crawling disabled)")
        
        page_data = fetch_url_content(root_url)
        
        if not page_data['success']:
            logger.warning(f"Failed to fetch URL {root_url}: {page_data['error']}")
            return []
        
        logger.info(f"Successfully fetched: {root_url} (Title: {page_data['title']}, {len(page_data['content'])} chars)")
        return [page_data]
    
    # ===== CRAWLING MODE (ENABLED) =====
    # Multi-page crawling with navbar-first strategy: main page → navbar links → nested links
    visited_urls: Set[str] = set()
    pages_data: List[Dict[str, any]] = []
    
    logger.info(f"Starting navbar-first crawl from: {root_url} (max {max_pages} pages)")
    
    # Step 1: Fetch the main/root page
    if len(pages_data) >= max_pages:
        return pages_data
        
    page_data = fetch_url_content(root_url)
    visited_urls.add(root_url)
    
    if not page_data['success']:
        logger.warning(f"Failed to fetch root URL {root_url}: {page_data['error']}")
        return pages_data
    
    pages_data.append(page_data)
    navbar_links = page_data['links']
    logger.info(f"Root page fetched. Found {len(navbar_links)} navbar links.")
    
    # Step 2: Crawl all navbar/header links from main page
    navbar_pages = []
    for navbar_url in navbar_links:
        if len(pages_data) >= max_pages:
            break
        
        if navbar_url in visited_urls:
            continue
        
        visited_urls.add(navbar_url)
        nav_page_data = fetch_url_content(navbar_url)
        
        if nav_page_data['success']:
            pages_data.append(nav_page_data)
            navbar_pages.append(nav_page_data)
            logger.info(f"Navbar page fetched: {navbar_url}")
        else:
            logger.warning(f"Failed to fetch navbar link {navbar_url}: {nav_page_data['error']}")
    
    # Step 3: Recursively crawl links within navbar pages (depth-first)
    for nav_page in navbar_pages:
        if len(pages_data) >= max_pages:
            break
        
        nested_links = nav_page['links']
        for nested_url in nested_links:
            if len(pages_data) >= max_pages:
                break
            
            if nested_url in visited_urls:
                continue
            
            visited_urls.add(nested_url)
            nested_page_data = fetch_url_content(nested_url)
            
            if nested_page_data['success']:
                pages_data.append(nested_page_data)
                logger.info(f"Nested page fetched: {nested_url}")
            else:
                logger.warning(f"Failed to fetch nested link {nested_url}")
    
    logger.info(f"Crawl complete: fetched {len(pages_data)} pages from {root_url}")
    return pages_data


def save_url_content(pages_data: List[Dict[str, any]], collection_name: str) -> List[str]:
    """Save crawled page content to domain-specific folders with URL-path-based names.
    
    Args:
        pages_data: List of page data dictionaries
        collection_name: Name for organizing saved files
        
    Returns:
        List of saved file paths
    """
    saved_files = []
    
    # Group pages by domain
    pages_by_domain = {}
    for page in pages_data:
        if not page['success'] or not page['content']:
            continue
        domain = page['domain']
        if domain not in pages_by_domain:
            pages_by_domain[domain] = []
        pages_by_domain[domain].append(page)
    
    # Save each domain's pages in separate folders
    for domain, domain_pages in pages_by_domain.items():
        # Create domain folder
        domain_folder = DATA_DIR / domain
        domain_folder.mkdir(parents=True, exist_ok=True)
        
        # Track filenames to handle duplicates
        used_filenames = set()
        
        for page in domain_pages:
            # Generate filename from URL path
            path_name = extract_path_name_from_url(page['url'])
            filename = f"{path_name}.html"
            
            # Handle duplicate filenames
            original_filename = filename
            counter = 1
            while filename in used_filenames:
                name_part = path_name
                filename = f"{name_part}-{counter}.html"
                counter += 1
            
            used_filenames.add(filename)
            filepath = domain_folder / filename
            
            # Extract display name (without .html extension)
            display_name = filename.replace('.html', '')
            
            # Create HTML document with enhanced metadata
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="source_url" content="{page['url']}">
    <meta name="domain" content="{page['domain']}">
    <meta name="page_title" content="{page['title']}">
    <meta name="display_name" content="{display_name}">
    <meta name="crawl_date" content="{datetime.now(IST).isoformat()}">
    <title>{page['title']}</title>
</head>
<body>
<h1>{page['title']}</h1>
<p><strong>Source:</strong> <a href="{page['url']}">{page['url']}</a></p>
<p><strong>Page:</strong> {display_name}</p>
<hr>
<div class="content">
{page['content']}
</div>
</body>
</html>"""
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(filepath))
                logger.info(f"Saved: {domain}/{filename} (display: {display_name})")
            except Exception as e:
                logger.error(f"Error saving {domain}/{filename}: {str(e)}")
    
    return saved_files


def get_unique_url_collection_name(urls: List[str]) -> str:
    """Generate a unique collection name based on URL domains.
    
    Args:
        urls: List of URLs
        
    Returns:
        Unique collection name
    """
    if not urls:
        return "website"
    
    # Get domain from first URL
    first_domain = extract_domain(urls[0])
    # Clean domain name for use in collection name
    base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', first_domain)
    base_name = re.sub(r'_+', '_', base_name).strip('_')
    
    # If multiple URLs, append count
    if len(urls) > 1:
        base_name = f"{base_name}_and_{len(urls) - 1}_more"
    
    # Check for existing sessions with same name
    from models.chat_storage import get_chat_storage
    storage = get_chat_storage()
    existing_sessions = storage.get_all_active_sessions()
    existing_names = {s['collection_name'] for s in existing_sessions}
    
    # Handle duplicates
    final_name = base_name
    counter = 1
    while final_name in existing_names:
        final_name = f"{base_name}_{counter}"
        counter += 1
    
    return final_name


def validate_and_fetch_urls(url_list: List[str]) -> Tuple[List[str], str, str, List[str], List[Dict[str, any]]]:
    """Validate URLs, crawl websites, and save content.
    
    Args:
        url_list: List of URLs to process
        
    Returns:
        Tuple of (saved_files, collection_name, document_name, original_urls, pages_metadata)
        - saved_files: List of paths to saved HTML files
        - collection_name: Name for the vector store collection
        - document_name: Display name for the session (domain-based)
        - original_urls: List of root URLs provided by user
        - pages_metadata: List of metadata for all crawled pages
    """
    if not url_list:
        raise gr.Error("⚠️ Please provide at least one URL.")
    
    # Clean and validate URLs
    cleaned_urls = []
    for url in url_list:
        url = url.strip()
        if not url:
            continue
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        cleaned_urls.append(url)
    
    if not cleaned_urls:
        raise gr.Error("⚠️ No valid URLs provided.")
    
    logger.info(f"Processing {len(cleaned_urls)} URLs")
    
    # Validate URLs
    valid_urls = []
    invalid_urls = []
    for url in cleaned_urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)
    
    if invalid_urls:
        logger.warning(f"Invalid/unreachable URLs: {invalid_urls}")
    
    if not valid_urls:
        raise gr.Error("❌ None of the provided URLs are valid or reachable. "
                      "Please check the URLs and try again.")
    
    # Generate collection name based on domains
    collection_name = get_unique_url_collection_name(valid_urls)
    
    # Fetch content from each URL (behavior controlled by ENABLE_CRAWLING config)
    all_pages_data = []
    for url in valid_urls:
        try:
            pages = crawl_website(url, max_pages=MAX_PAGES_PER_URL)
            all_pages_data.extend(pages)
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
    
    if not all_pages_data:
        raise gr.Error("❌ Failed to fetch content from any of the provided URLs. "
                      "Please check the URLs and try again.")
    
    # Save all crawled content
    saved_files = save_url_content(all_pages_data, collection_name)
    
    if not saved_files:
        raise gr.Error("❌ Failed to save any content from the URLs.")
    
    # Create document name from unique domains
    unique_domains = list(set([page['domain'] for page in all_pages_data]))
    if len(unique_domains) == 1:
        document_name = unique_domains[0]
    else:
        document_name = f"{unique_domains[0]} and {len(unique_domains) - 1} more"
    
    # Extract metadata for each page (for source citations)
    pages_metadata = [
        {
            'url': page['url'],
            'title': page['title'],
            'domain': page['domain']
        }
        for page in all_pages_data if page['success']
    ]
    
    logger.info(f"URL ingestion complete: {len(saved_files)} pages saved, "
               f"collection: {collection_name}, display: {document_name}")
    
    return saved_files, collection_name, document_name, valid_urls, pages_metadata


__all__ = [
    "validate_url",
    "extract_domain",
    "fetch_url_content",
    "crawl_website",
    "validate_and_fetch_urls",
    "get_unique_url_collection_name"
]
