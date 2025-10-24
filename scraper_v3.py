"""
Intelligent web scraping with improved link detection and language filtering
VERSION 3: Enhanced with enterprise signal detection
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Set
import re
from langdetect import detect, LangDetectException


class IntelligentScraper:
    """Scrapes company websites with smart link detection and English filtering"""

    def __init__(self, max_pages: int = 10, timeout: int = 30):
        self.max_pages = max_pages
        self.timeout = timeout
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        # Enable connection pooling for faster requests
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Comprehensive priority keywords
        self.priority_keywords = [
            'about', 'company', 'who-we-are', 'our-story', 'overview', 'about-us',
            'services', 'solutions', 'products', 'what-we-do', 'offerings', 'capabilities',
            'technology', 'innovation', 'ai', 'artificial-intelligence', 'digital', 'ml',
            'machine-learning', 'data', 'analytics', 'automation',
            'case-studies', 'portfolio', 'work', 'projects', 'success', 'clients',
            'testimonials', 'success-stories', 'customers', 'case-study',
            'team', 'leadership', 'people', 'executives', 'our-team',
            'careers', 'jobs', 'join-us', 'work-with-us',
            'news', 'blog', 'insights', 'resources', 'press'
        ]

        # High-value link text patterns
        self.priority_link_texts = [
            'about us', 'about', 'company', 'who we are', 'our company', 'company info',
            'about the company', 'learn more', 'our story',
            'products', 'our products', 'services', 'our services', 'solutions',
            'what we do', 'offerings', 'capabilities',
            'technology', 'innovation', 'ai', 'artificial intelligence',
            'machine learning', 'data analytics', 'automation',
            'case studies', 'portfolio', 'our work', 'projects', 'success stories',
            'client stories', 'customer success',
            'team', 'leadership', 'our team', 'people', 'meet the team',
            'careers', 'join us', 'work with us', 'jobs'
        ]

        # Enterprise signal patterns for detection
        self.enterprise_patterns = {
            'fortune': r'fortune\s+(?:500|100)',
            'publicly_traded': r'(?:publicly traded|publicly-traded|public company|traded on)',
            'stock_exchange': r'(?:nasdaq|nyse|dow jones|s&p 500)',
            'large_valuation': r'\$\d+(?:\.\d+)?\s*(?:billion|B)\s+(?:market cap|valuation)',
            'large_workforce': r'(?:\d{2,3},000\+|10,000\+|20,000\+)\s+employees',
            'multinational': r'multinational\s+corporation',
            'global_offices': r'offices in \d{2,}\+?\s+countries',
            'large_revenue': r'\$\d+(?:\.\d+)?\s*(?:billion|B)\s+in revenue'
        }

    def detect_enterprise_signals(self, text: str) -> Dict[str, List[str]]:
        """
        Detect enterprise-scale indicators in scraped text

        Returns:
            Dict with signal types and matched text snippets
        """
        detected = {}
        text_lower = text.lower()

        for signal_name, pattern in self.enterprise_patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                detected[signal_name] = matches

        return detected

    def is_english(self, text: str) -> bool:
        """Check if text is in English"""
        if not text or len(text.strip()) < 50:
            return True  # Too short to detect, assume English

        try:
            # Sample first 200 chars for faster detection
            sample = text[:200].strip()
            lang = detect(sample)
            return lang == 'en'
        except LangDetectException:
            return True  # If detection fails, assume English

    def normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        parsed = urlparse(url)
        # Remove trailing slash and fragments
        path = parsed.path.rstrip('/')
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid for crawling"""
        try:
            parsed = urlparse(url)

            # Must have same domain
            if base_domain not in parsed.netloc:
                return False

            # Skip file downloads
            skip_extensions = [
                '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                '.zip', '.tar', '.gz', '.rar',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.mp4', '.mp3', '.avi', '.mov', '.wav',
                '.css', '.js', '.xml', '.json'
            ]
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                return False

            # Skip utility pages
            skip_patterns = [
                'login', 'signin', 'sign-in', 'signup', 'sign-up', 'register',
                'cart', 'checkout', 'payment', 'account', 'profile',
                'search', 'filter', 'sort',
                'privacy', 'terms', 'cookie', 'legal', 'disclaimer',
                'wp-admin', 'wp-content', 'wp-includes',
                'feed', 'rss', 'atom',
                '#', 'javascript:', 'mailto:', 'tel:'
            ]
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in skip_patterns):
                return False

            return True
        except:
            return False

    def score_url_priority(self, url: str, link_text: str, anchor_context: str = '') -> int:
        """Enhanced scoring based on URL, link text, and surrounding context"""
        url_lower = url.lower()
        text_lower = link_text.lower().strip()
        context_lower = anchor_context.lower().strip()
        score = 0

        # Score URL keywords (10 points each)
        for keyword in self.priority_keywords:
            if keyword in url_lower:
                score += 10

        # Score link text (20 points - higher weight for visible text)
        for pattern in self.priority_link_texts:
            if pattern in text_lower:
                score += 20
                break  # Only count once

        # Bonus for context around link (5 points)
        for keyword in self.priority_keywords:
            if keyword in context_lower:
                score += 5
                break

        # Prefer shorter paths (closer to root) but don't go negative
        path_depth = url_lower.count('/')
        if path_depth > 3:
            score -= (path_depth - 3) * 2  # Only penalize very deep paths

        # Major boost for high-value combinations
        high_value_combos = [
            ('about', 'company'),
            ('our', 'services'),
            ('what', 'do'),
            ('case', 'stud'),
            ('success', 'stor'),
            ('our', 'team'),
            ('artificial', 'intelligence'),
            ('machine', 'learning')
        ]

        combined = url_lower + ' ' + text_lower + ' ' + context_lower
        for word1, word2 in high_value_combos:
            if word1 in combined and word2 in combined:
                score += 25

        # Give at least 1 point to internal links that passed validation
        # This ensures we crawl some pages even if no keywords match
        if score == 0 and len(url_lower) > 0:
            score = 1

        return score

    def extract_text_from_html(self, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            element.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def extract_company_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract company name from page"""
        # Try og:site_name
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            return og_site['content'].strip()

        # Try title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            # Split by common separators
            for sep in ['|', '-', '–', ':', '—']:
                if sep in title_text:
                    name = title_text.split(sep)[0].strip()
                    if 3 < len(name) < 50:
                        return name
            if 3 < len(title_text) < 50:
                return title_text

        # Fallback to domain
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
        return domain.capitalize()

    def scrape_page(self, url: str) -> Dict:
        """Scrape single page"""
        try:
            response = self.session.get(url, timeout=7, allow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')  # lxml is faster than html.parser

            # Extract text
            text = self.extract_text_from_html(soup)

            # Check if English
            if not self.is_english(text):
                print(f"  X Skipped (non-English): {url}")
                return {
                    'url': url,
                    'text': '',
                    'links': [],
                    'soup': None,
                    'success': False,
                    'error': 'Non-English content'
                }

            # Detect enterprise signals (NEW in v3)
            enterprise_signals = self.detect_enterprise_signals(text)

            # Find all links with context
            links_data = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue

                absolute_url = urljoin(url, href)
                link_text = link.get_text(strip=True)

                # Get surrounding context (parent element text)
                context = ''
                if link.parent:
                    context = link.parent.get_text(strip=True)[:100]

                links_data.append({
                    'url': absolute_url,
                    'text': link_text,
                    'context': context
                })

            return {
                'url': url,
                'text': text,
                'links': links_data,
                'soup': soup,
                'success': True,
                'enterprise_signals': enterprise_signals  # NEW: Return detected signals
            }

        except Exception as e:
            return {
                'url': url,
                'text': '',
                'links': [],
                'soup': None,
                'success': False,
                'error': str(e)
            }

    def crawl_website(self, start_url: str) -> Dict:
        """Crawl website with improved link detection"""
        start_time = time.time()

        if not start_url.startswith('http'):
            start_url = 'https://' + start_url

        base_domain = urlparse(start_url).netloc

        results = {
            'company_name': '',
            'base_url': start_url,
            'pages_scraped': [],
            'total_text': '',
            'page_count': 0,
            'enterprise_signals': {}  # NEW: Track enterprise signals across all pages
        }

        print(f"\n{'='*80}")
        print(f"CRAWLING: {start_url}")
        print(f"{'='*80}")

        all_signals = {}

        try:
            # Scrape homepage
            print("\nScraping homepage...")
            homepage = self.scrape_page(start_url)

            if not homepage['success']:
                results['error'] = f"Failed to scrape: {homepage.get('error')}"
                return results

            # Extract company name
            results['company_name'] = self.extract_company_name(homepage['soup'], start_url)
            print(f"  + Company: {results['company_name']}")
            print(f"  + Content: {len(homepage['text'])} chars")

            # Collect enterprise signals from homepage
            if homepage.get('enterprise_signals'):
                for signal_type, matches in homepage['enterprise_signals'].items():
                    if signal_type not in all_signals:
                        all_signals[signal_type] = []
                    all_signals[signal_type].extend(matches)
                print(f"  + Enterprise signals found: {len(homepage['enterprise_signals'])} types")

            # Store homepage
            self.visited_urls.add(self.normalize_url(start_url))
            results['pages_scraped'].append({
                'url': start_url,
                'title': 'Homepage',
                'text_length': len(homepage['text'])
            })
            results['total_text'] += homepage['text'] + '\n\n'
            results['page_count'] = 1

            # Score and sort links
            print(f"\nDiscovering links...")
            print(f"  Total links found: {len(homepage['links'])}")
            scored_links = []
            filtered_count = 0

            for link_data in homepage['links']:
                link_url = link_data['url']
                normalized = self.normalize_url(link_url)

                if normalized in self.visited_urls:
                    filtered_count += 1
                    continue

                if not self.is_valid_url(link_url, base_domain):
                    filtered_count += 1
                    continue

                score = self.score_url_priority(
                    link_url,
                    link_data['text'],
                    link_data.get('context', '')
                )

                # Accept all links that have positive score (including 1 point fallback)
                if score > 0:
                    scored_links.append((score, link_url, link_data['text']))

            # Take top priority links
            scored_links.sort(reverse=True, key=lambda x: x[0])
            priority_links = scored_links[:self.max_pages - 1]

            print(f"  + Valid links after filtering: {len(scored_links)}")
            print(f"  + Filtered out: {filtered_count}")
            print(f"  + Priority links to crawl: {len(priority_links)}")

            # Crawl priority pages
            print(f"\nCrawling pages...")
            for score, url, link_text in priority_links:
                if time.time() - start_time > self.timeout:
                    print(f"  ! Timeout reached")
                    break

                normalized = self.normalize_url(url)
                if normalized in self.visited_urls:
                    continue

                print(f"  - {link_text[:50] if link_text else 'Page'}...")
                page = self.scrape_page(url)

                if page['success']:
                    self.visited_urls.add(normalized)

                    # Collect enterprise signals from this page
                    if page.get('enterprise_signals'):
                        for signal_type, matches in page['enterprise_signals'].items():
                            if signal_type not in all_signals:
                                all_signals[signal_type] = []
                            all_signals[signal_type].extend(matches)

                    title = link_text[:50] if link_text else 'Page'
                    results['pages_scraped'].append({
                        'url': url,
                        'title': title,
                        'text_length': len(page['text'])
                    })
                    results['total_text'] += f"\n\n=== {title} ===\n\n{page['text']}"
                    results['page_count'] += 1

                    print(f"    + {len(page['text'])} chars")

                time.sleep(0.1)  # Minimal delay for faster crawling

        except Exception as e:
            print(f"  X Error: {str(e)}")
            results['error'] = str(e)

        # Store aggregated enterprise signals
        results['enterprise_signals'] = all_signals

        elapsed = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"COMPLETE: {results['page_count']} pages in {elapsed:.1f}s")

        # Print enterprise signals summary
        if all_signals:
            print(f"\nENTERPRISE SIGNALS DETECTED:")
            for signal_type, matches in all_signals.items():
                print(f"  - {signal_type}: {len(matches)} occurrence(s)")

        print(f"{'='*80}\n")

        return results


def scrape_company_website(url: str, max_pages: int = 10) -> Dict:
    """Main scraping function"""
    scraper = IntelligentScraper(max_pages=max_pages)
    return scraper.crawl_website(url)
