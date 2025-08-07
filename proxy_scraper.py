#!/usr/bin/env python3
"""
Proxy Scraper - Scrapes proxies from websites and categorizes them
Supports automatic pagination and filtering by HTTP/HTTPS, SOCKS4, and SOCKS5
"""

import requests
import re
import time
import threading
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from datetime import datetime

class ProxyScraper:
    def __init__(self, max_workers=10, delay=1):
        self.max_workers = max_workers
        self.delay = delay  # Delay between requests to be respectful
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Proxy storage
        self.all_proxies = set()
        
        # Thread lock
        self.lock = threading.Lock()
        
        # File for instant saving
        self.proxy_file = "proxy_list.txt"
        
        # Load existing proxies if file exists
        self.load_existing_proxies()
        
        # Proxy patterns
        self.proxy_patterns = [
            # IP:PORT format
            r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b',
            # Alternative formats with spaces
            r'\b(?:\d{1,3}\s*\.\s*){3}\d{1,3}\s*:\s*\d{1,5}\b',
        ]
        
        # Common pagination patterns
        self.pagination_patterns = [
            r'next\s*page',
            r'next\s*>',
            r'>\s*next',
            r'page\s*\d+',
            r'more\s*proxies',
            r'continue',
            r'load\s*more'
        ]

    def load_existing_proxies(self):
        """Load existing proxies from proxy_list.txt to avoid duplicates"""
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r') as f:
                    existing_proxies = set(line.strip() for line in f if line.strip())
                    self.all_proxies.update(existing_proxies)
                print(f"Loaded {len(existing_proxies)} existing proxies from {self.proxy_file}")
        except Exception as e:
            print(f"Error loading existing proxies: {e}")

    def save_proxy_instantly(self, proxy):
        """Save a single proxy to file instantly"""
        try:
            with open(self.proxy_file, 'a') as f:
                f.write(f"{proxy}\n")
                f.flush()  # Force write to disk
        except Exception as e:
            print(f"Error saving proxy {proxy}: {e}")

    def extract_proxies_from_text(self, text):
        """Extract proxy addresses from text using regex"""
        proxies = set()
        
        for pattern in self.proxy_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the proxy (remove spaces)
                proxy = re.sub(r'\s+', '', match)
                # Validate format
                if self.validate_proxy_format(proxy):
                    proxies.add(proxy)
        
        return proxies

    def validate_proxy_format(self, proxy):
        """Validate proxy format (IP:PORT)"""
        try:
            ip, port = proxy.split(':')
            
            # Validate IP
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            
            # Validate port
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                return False
                
            return True
        except:
            return False

    def scrape_page(self, url, max_pages=5):
        """Scrape proxies from a single page and follow pagination"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=15)  # Increased timeout
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Extract proxies
            proxies = self.extract_proxies_from_text(page_text)
            
            if proxies:
                new_proxies = []
                
                # Process proxies without categorization
                for proxy in proxies:
                    with self.lock:
                        # Check if proxy is new
                        if proxy not in self.all_proxies:
                            self.all_proxies.add(proxy)
                            new_proxies.append(proxy)
                            
                            # Save instantly to file
                            self.save_proxy_instantly(proxy)
                
                if new_proxies:
                    print(f"Found {len(new_proxies)} new proxies on {url} (saved instantly)")
                else:
                    print(f"Found {len(proxies)} proxies on {url} (all duplicates)")
            else:
                print(f"No proxies found on {url}")
            
            # Skip pagination for GitHub raw files
            if 'raw.githubusercontent.com' in url or 'github.com' in url:
                print(f"Skipping pagination for GitHub URL: {url}")
                return
            
            # Look for pagination links (limit to prevent infinite loops)
            if max_pages > 1:
                next_links = self.find_pagination_links(soup, url)
                if next_links:
                    print(f"Found {len(next_links)} pagination links, processing first {min(len(next_links), max_pages-1)}")
                    for next_url in next_links[:max_pages-1]:  # Limit pagination
                        time.sleep(self.delay)
                        self.scrape_page(next_url, max_pages=1)  # Avoid infinite recursion
            
        except requests.exceptions.Timeout:
            print(f"Timeout scraping {url} - skipping")
        except requests.exceptions.RequestException as e:
            print(f"Request error scraping {url}: {e}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    def find_pagination_links(self, soup, base_url):
        """Find pagination links on the page"""
        pagination_links = []
        
        # Look for common pagination patterns
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().lower().strip()
            link_href = link['href']
            
            # Check if link text matches pagination patterns
            for pattern in self.pagination_patterns:
                if re.search(pattern, link_text, re.IGNORECASE):
                    full_url = urljoin(base_url, link_href)
                    if full_url != base_url and full_url not in pagination_links:
                        pagination_links.append(full_url)
                        break
        
        # Look for numbered pagination
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().strip()
            if re.match(r'^\d+$', link_text):  # Pure numbers
                full_url = urljoin(base_url, link['href'])
                if full_url != base_url and full_url not in pagination_links:
                    pagination_links.append(full_url)
        
        return pagination_links

    def scrape_urls(self, urls, max_pages_per_site=5):
        """Scrape multiple URLs with threading"""
        print(f"Starting to scrape {len(urls)} URLs with {self.max_workers} workers...")
        print(f"Max pages per site: {max_pages_per_site}")
        print("=" * 60)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit scraping tasks
            future_to_url = {
                executor.submit(self.scrape_page, url, max_pages_per_site): url 
                for url in urls
            }
            
            # Wait for completion with timeout and progress tracking
            completed = 0
            total = len(future_to_url)
            
            for future in as_completed(future_to_url, timeout=300):  # 5 minute timeout
                url = future_to_url[future]
                completed += 1
                try:
                    future.result()
                    print(f"Progress: {completed}/{total} URLs completed")
                except Exception as e:
                    print(f"Error processing {url}: {e}")
            
            print(f"Scraping phase completed: {completed}/{total} URLs processed")

    def save_results(self, output_dir=""):
        """Save summary and clean up proxy_list.txt"""
        # Clean up proxy_list.txt by removing duplicates and sorting
        if self.all_proxies:
            try:
                with open(self.proxy_file, 'w') as f:
                    f.write('\n'.join(sorted(self.all_proxies)))
                print(f"Final proxy list cleaned and saved to: {self.proxy_file}")
            except Exception as e:
                print(f"Error cleaning up proxy file: {e}")
        
        # Save summary
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = {
            'timestamp': timestamp,
            'total_proxies': len(self.all_proxies)
        }
        
        summary_file = os.path.join(output_dir, f"scrape_summary_{timestamp}.json") if output_dir else f"scrape_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary

    def display_results(self):
        """Display scraping results"""
        print("\n" + "=" * 60)
        print("PROXY SCRAPING RESULTS")
        print("=" * 60)
        print(f"Total unique proxies found: {len(self.all_proxies)}")
        print("=" * 60)

def load_urls_from_file(filename):
    """Load URLs from a text file"""
    try:
        with open(filename, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return urls
    except FileNotFoundError:
        print(f"File {filename} not found!")
        return []

def main():
    """Main function"""
    print("Proxy Scraper v1.0")
    print("==================")
    
    # Configuration
    MAX_WORKERS = 15
    DELAY = 1  # seconds between requests
    MAX_PAGES_PER_SITE = 5
    
    print(f"Configuration:")
    print(f"- Max workers: {MAX_WORKERS}")
    print(f"- Delay between requests: {DELAY}s")
    print(f"- Max pages per site: {MAX_PAGES_PER_SITE}")
    print()
    
    # Get URLs to scrape
    print("Choose input method:")
    print("1. Enter URLs manually")
    print("2. Load URLs from file")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    urls = []
    
    if choice == "1":
        print("\nEnter URLs to scrape (one per line, empty line to finish):")
        while True:
            url = input("URL: ").strip()
            if not url:
                break
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            urls.append(url)
    
    elif choice == "2":
        filename = input("Enter filename containing URLs: ").strip()
        if not filename:
            filename = "proxy_sources.txt"
        urls = load_urls_from_file(filename)
    
    else:
        print("No proxies provided. Exiting.")
        return
        
    if not urls:
        print("No URLs provided. Exiting.")
        return
    
    print(f"\nWill scrape {len(urls)} URLs:")
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")
    
    # Create scraper and run
    scraper = ProxyScraper(max_workers=MAX_WORKERS, delay=DELAY)
    
    try:
        print(f"\nProxies will be saved instantly to: {scraper.proxy_file}")
        print("You can cancel anytime with Ctrl+C and keep what's already scraped.\n")
        
        start_time = time.time()
        scraper.scrape_urls(urls, max_pages_per_site=MAX_PAGES_PER_SITE)
        end_time = time.time()
        
        # Display and save results
        scraper.display_results()
        summary = scraper.save_results()
        
        print(f"\nScraping completed in {end_time - start_time:.2f} seconds")
        
        # Ask if user wants to run proxy checker
        if scraper.all_proxies:
            check_proxies = input("\nDo you want to check the scraped proxies now? (y/n): ").strip().lower()
            if check_proxies == 'y':
                print("\nYou can now run: python proxy_checker.py")
                print("It will automatically use the proxy_list.txt file.")
        
    except KeyboardInterrupt:
        print("\n\nScraping cancelled by user.")
        print(f"Proxies scraped so far have been saved to: {scraper.proxy_file}")
        scraper.display_results()
        scraper.save_results()  # Clean up and save summary
        print("You can resume scraping or run the checker with the current proxy list.")

if __name__ == "__main__":
    main()
