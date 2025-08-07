#!/usr/bin/env python3
"""
Integrated Proxy Tool - Combines scraping and checking functionality
Scrapes proxies from websites and then checks them for working status
"""

import argparse
import sys
import os
from proxy_scraper import ProxyScraper
from proxy_checker import ProxyChecker

def main():
    parser = argparse.ArgumentParser(description='Integrated Proxy Scraper and Checker')
    parser.add_argument('--mode', choices=['scrape', 'check', 'both'], default='both',
                       help='Mode: scrape only, check only, or both')
    parser.add_argument('--urls', nargs='+', help='URLs to scrape proxies from')
    parser.add_argument('--url-file', help='File containing URLs to scrape')
    parser.add_argument('--proxy-file', help='File containing proxies to check')
    parser.add_argument('--max-workers', type=int, default=50, help='Number of worker threads')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for proxy testing')
    parser.add_argument('--max-pages', type=int, default=5, help='Max pages to scrape per site')
    parser.add_argument('--delay', type=float, default=1, help='Delay between scraping requests')
    
    args = parser.parse_args()
    
    print("Integrated Proxy Tool v1.0")
    print("=" * 40)
    
    # If no mode specified and running interactively, ask user
    if len(sys.argv) == 1:  # No arguments provided
        print("\nSelect mode:")
        print("1. Scrape only")
        print("2. Check only") 
        print("3. Both (scrape then check)")
        
        while True:
            choice = input("\nEnter choice (1-3): ").strip()
            if choice == '1':
                args.mode = 'scrape'
                break
            elif choice == '2':
                args.mode = 'check'
                break
            elif choice == '3':
                args.mode = 'both'
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    scraped_proxies_file = None
    
    # Scraping phase
    if args.mode in ['scrape', 'both']:
        print("\n[SCRAPING PHASE]")
        scraper = ProxyScraper(max_workers=args.max_workers, delay=args.delay)
        
        urls = []
        if args.urls:
            urls = args.urls
        elif args.url_file:
            try:
                with open(args.url_file, 'r') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except FileNotFoundError:
                print(f"URL file {args.url_file} not found!")
                return
        else:
            # Check for default proxy_sources.txt file
            if os.path.exists("proxy_sources.txt"):
                print("No URLs specified, using default proxy_sources.txt")
                try:
                    with open("proxy_sources.txt", 'r') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    print(f"Loaded {len(urls)} URLs from proxy_sources.txt")
                except Exception as e:
                    print(f"Error reading proxy_sources.txt: {e}")
                    return
            else:
                # Interactive mode for URL input
                print("\nNo proxy_sources.txt found. Enter URLs to scrape (one per line, empty line to finish):")
                while True:
                    url = input("URL: ").strip()
                    if not url:
                        break
                    if not url.startswith(('http://', 'https://')):
                        url = 'http://' + url
                    urls.append(url)
        
        if not urls:
            print("No URLs provided for scraping!")
            if args.mode == 'scrape':
                return
        else:
            scraper.scrape_urls(urls, max_pages_per_site=args.max_pages)
            scraper.display_results()
            summary = scraper.save_results()
            
            # Save scraped proxies for checking
            if scraper.all_proxies:
                scraped_proxies_file = "temp_scraped_proxies.txt"
                with open(scraped_proxies_file, 'w') as f:
                    f.write('\n'.join(sorted(scraper.all_proxies)))
                print(f"\nScraped proxies saved to: {scraped_proxies_file}")
    
    # Checking phase
    if args.mode in ['check', 'both']:
        print("\n[CHECKING PHASE]")
        checker = ProxyChecker(timeout=args.timeout, max_workers=args.max_workers)
        
        proxy_file = None
        if args.proxy_file:
            proxy_file = args.proxy_file
        elif scraped_proxies_file and os.path.exists(scraped_proxies_file):
            proxy_file = scraped_proxies_file
        elif os.path.exists("proxy_list.txt"):
            proxy_file = "proxy_list.txt"
        else:
            print("No proxy file specified and no default found!")
            return
        
        checker.run_check(proxy_file)
        
        # Clean up temporary file
        if scraped_proxies_file and os.path.exists(scraped_proxies_file):
            try:
                os.remove(scraped_proxies_file)
                print(f"\nCleaned up temporary file: {scraped_proxies_file}")
            except:
                pass

if __name__ == "__main__":
    main()
