#!/usr/bin/env python3
"""
Proxy Checker - Tests proxy list and categorizes by type
Supports HTTP/HTTPS, SOCKS4, and SOCKS5 proxies with multithreading
"""

import requests
import socket
import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import socks
import warnings

# Suppress urllib3 warnings
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

class ProxyChecker:
    def __init__(self, timeout=10, max_workers=50):
        self.timeout = timeout
        self.max_workers = max_workers
        self.test_url = "http://httpbin.org/ip"
        self.test_url_https = "https://httpbin.org/ip"
        
        # Results storage
        self.working_http = []
        self.working_https = []
        self.working_socks4 = []
        self.working_socks5 = []
        self.failed_proxies = []
        
        # Thread lock for safe writing
        self.lock = threading.Lock()
        
        # Progress tracking
        self.total_proxies = 0
        self.checked_proxies = 0
        self.last_save_count = 0  # Track when we last saved
        self.save_interval = 500  # Save every 500 proxies
        
        # Total counts for final display
        self.total_working_http = 0
        self.total_working_https = 0
        self.total_working_socks4 = 0
        self.total_working_socks5 = 0
        self.total_failed_proxies = 0
        
        # Initialize file names with timestamp
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.file_names = {
            'http': f'working_http_proxies_{self.timestamp}.txt',
            'https': f'working_https_proxies_{self.timestamp}.txt',
            'socks4': f'working_socks4_proxies_{self.timestamp}.txt',
            'socks5': f'working_socks5_proxies_{self.timestamp}.txt',
            'failed': f'failed_proxies_{self.timestamp}.txt'
        }

    def load_proxies(self, file_path):
        """Load proxies from file and remove duplicates"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Load all lines and remove duplicates using set
                all_lines = [line.strip() for line in f if line.strip()]
                proxies = list(set(all_lines))  # Remove duplicates
            
            original_count = len(all_lines)
            unique_count = len(proxies)
            duplicates_removed = original_count - unique_count
            
            self.total_proxies = unique_count
            print(f"Loaded {original_count} proxies from {file_path}")
            if duplicates_removed > 0:
                print(f"Removed {duplicates_removed} duplicates - {unique_count} unique proxies to check")
            else:
                print(f"No duplicates found - {unique_count} unique proxies to check")
            
            return proxies
        except FileNotFoundError:
            print(f"Error: File {file_path} not found!")
            return []
        except Exception as e:
            print(f"Error loading proxies: {e}")
            return []

    def test_http_proxy(self, proxy):
        """Test HTTP proxy"""
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            response = requests.get(
                self.test_url,
                proxies=proxy_dict,
                timeout=self.timeout,
                verify=False
            )
            
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def test_https_proxy(self, proxy):
        """Test HTTPS proxy"""
        try:
            proxy_dict = {
                'http': f'https://{proxy}',
                'https': f'https://{proxy}'
            }
            
            response = requests.get(
                self.test_url_https,
                proxies=proxy_dict,
                timeout=self.timeout,
                verify=False
            )
            
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def test_socks4_proxy(self, proxy):
        """Test SOCKS4 proxy"""
        try:
            ip, port = proxy.split(':')
            port = int(port)
            
            # Create socket and set SOCKS4 proxy
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS4, ip, port)
            sock.settimeout(self.timeout)
            
            # Try to connect to a test server
            sock.connect(("httpbin.org", 80))
            sock.close()
            return True
        except:
            pass
        return False

    def save_intermediate_results(self):
        """Save intermediate results to files (append mode)"""
        # Save working proxies by type (append mode)
        if self.working_http:
            with open(self.file_names['http'], 'a') as f:
                f.write('\n'.join(self.working_http) + '\n')
            self.total_working_http += len(self.working_http)
            self.working_http.clear()  # Clear the list after saving
        
        if self.working_https:
            with open(self.file_names['https'], 'a') as f:
                f.write('\n'.join(self.working_https) + '\n')
            self.total_working_https += len(self.working_https)
            self.working_https.clear()
        
        if self.working_socks4:
            with open(self.file_names['socks4'], 'a') as f:
                f.write('\n'.join(self.working_socks4) + '\n')
            self.total_working_socks4 += len(self.working_socks4)
            self.working_socks4.clear()
        
        if self.working_socks5:
            with open(self.file_names['socks5'], 'a') as f:
                f.write('\n'.join(self.working_socks5) + '\n')
            self.total_working_socks5 += len(self.working_socks5)
            self.working_socks5.clear()
        
        # Save failed proxies (append mode)
        if self.failed_proxies:
            with open(self.file_names['failed'], 'a') as f:
                f.write('\n'.join(self.failed_proxies) + '\n')
            self.total_failed_proxies += len(self.failed_proxies)
            self.failed_proxies.clear()
        
        print(f"\n[SAVED] Intermediate results saved after {self.checked_proxies} proxies")
        self.last_save_count = self.checked_proxies

    def test_socks5_proxy(self, proxy):
        """Test SOCKS5 proxy"""
        try:
            ip, port = proxy.split(':')
            port = int(port)
            
            # Create socket and set SOCKS5 proxy
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS5, ip, port)
            sock.settimeout(self.timeout)
            
            # Try to connect to a test server
            sock.connect(("httpbin.org", 80))
            sock.close()
            return True
        except:
            pass
        return False

    def check_proxy(self, proxy):
        """Check a single proxy against all types"""
        results = {
            'proxy': proxy,
            'http': False,
            'https': False,
            'socks4': False,
            'socks5': False
        }
        
        # Test HTTP
        if self.test_http_proxy(proxy):
            results['http'] = True
        
        # Test HTTPS
        if self.test_https_proxy(proxy):
            results['https'] = True
        
        # Test SOCKS4
        if self.test_socks4_proxy(proxy):
            results['socks4'] = True
        
        # Test SOCKS5
        if self.test_socks5_proxy(proxy):
            results['socks5'] = True
        
        # Update progress and results
        with self.lock:
            self.checked_proxies += 1
            
            if results['http']:
                self.working_http.append(proxy)
            if results['https']:
                self.working_https.append(proxy)
            if results['socks4']:
                self.working_socks4.append(proxy)
            if results['socks5']:
                self.working_socks5.append(proxy)
            
            if not any([results['http'], results['https'], results['socks4'], results['socks5']]):
                self.failed_proxies.append(proxy)
            
            # Check if we need to save intermediate results
            if self.checked_proxies - self.last_save_count >= self.save_interval:
                self.save_intermediate_results()
            
            # Progress update
            progress = (self.checked_proxies / self.total_proxies) * 100
            print(f"\rProgress: {self.checked_proxies}/{self.total_proxies} ({progress:.1f}%) - "
                  f"HTTP: {len(self.working_http)}, HTTPS: {len(self.working_https)}, "
                  f"SOCKS4: {len(self.working_socks4)}, SOCKS5: {len(self.working_socks5)}", end='')
        
        return results

    def run_check(self, proxy_file):
        """Run the proxy check with multithreading"""
        proxies = self.load_proxies(proxy_file)
        if not proxies:
            return
        
        print(f"\nStarting proxy check with {self.max_workers} threads...")
        print("Testing each proxy for HTTP, HTTPS, SOCKS4, and SOCKS5 support...\n")
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent checking
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_proxy = {executor.submit(self.check_proxy, proxy): proxy for proxy in proxies}
            
            # Wait for completion
            for future in as_completed(future_to_proxy):
                try:
                    future.result()
                except Exception as e:
                    proxy = future_to_proxy[future]
                    print(f"\nError checking {proxy}: {e}")
        
        end_time = time.time()
        self.display_results(end_time - start_time)

    def save_results(self):
        """Save final remaining results to files"""
        # Save any remaining proxies that haven't been saved yet
        if (self.working_http or self.working_https or self.working_socks4 or 
            self.working_socks5 or self.failed_proxies):
            
            if self.working_http:
                with open(self.file_names['http'], 'a') as f:
                    f.write('\n'.join(self.working_http) + '\n')
                self.total_working_http += len(self.working_http)
                print(f"Final HTTP proxies appended to: {self.file_names['http']}")
            
            if self.working_https:
                with open(self.file_names['https'], 'a') as f:
                    f.write('\n'.join(self.working_https) + '\n')
                self.total_working_https += len(self.working_https)
                print(f"Final HTTPS proxies appended to: {self.file_names['https']}")
            
            if self.working_socks4:
                with open(self.file_names['socks4'], 'a') as f:
                    f.write('\n'.join(self.working_socks4) + '\n')
                self.total_working_socks4 += len(self.working_socks4)
                print(f"Final SOCKS4 proxies appended to: {self.file_names['socks4']}")
            
            if self.working_socks5:
                with open(self.file_names['socks5'], 'a') as f:
                    f.write('\n'.join(self.working_socks5) + '\n')
                self.total_working_socks5 += len(self.working_socks5)
                print(f"Final SOCKS5 proxies appended to: {self.file_names['socks5']}")
            
            if self.failed_proxies:
                with open(self.file_names['failed'], 'a') as f:
                    f.write('\n'.join(self.failed_proxies) + '\n')
                self.total_failed_proxies += len(self.failed_proxies)
                print(f"Final failed proxies appended to: {self.file_names['failed']}")
        
        print(f"\nAll results have been saved to files with timestamp: {self.timestamp}")

    def display_results(self, duration):
        """Display final results"""
        print(f"\n\n{'='*60}")
        print("PROXY CHECK RESULTS")
        print(f"{'='*60}")
        print(f"Total proxies tested: {self.total_proxies}")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"Average time per proxy: {duration/self.total_proxies:.2f} seconds")
        print()
        print(f"Working HTTP proxies:  {self.total_working_http}")
        print(f"Working HTTPS proxies: {self.total_working_https}")
        print(f"Working SOCKS4 proxies: {self.total_working_socks4}")
        print(f"Working SOCKS5 proxies: {self.total_working_socks5}")
        print(f"Failed proxies: {self.total_failed_proxies}")
        print()
        
        total_working = self.total_working_http + self.total_working_https + self.total_working_socks4 + self.total_working_socks5
        # Remove duplicates by using unique proxies (some proxies might work for multiple types)
        success_rate = (total_working / self.total_proxies) * 100 if total_working <= self.total_proxies else ((self.total_proxies - self.total_failed_proxies) / self.total_proxies) * 100
        print(f"Success rate: {success_rate:.1f}%")
        print(f"{'='*60}")
        
        # Save results to files
        self.save_results()

def main():
    """Main function"""
    # Configuration
    PROXY_FILE = "proxy_list.txt"
    TIMEOUT = 10  # seconds
    MAX_WORKERS = 50  # number of threads
    
    print("Proxy Checker v1.0")
    print("==================")
    print(f"Configuration:")
    print(f"- Timeout: {TIMEOUT} seconds")
    print(f"- Max threads: {MAX_WORKERS}")
    print(f"- Proxy file: {PROXY_FILE}")
    print()
    
    # Create checker instance
    checker = ProxyChecker(timeout=TIMEOUT, max_workers=MAX_WORKERS)
    
    # Run the check
    try:
        checker.run_check(PROXY_FILE)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        print("Partial results:")
        checker.display_results(0)
    except Exception as e:
        print(f"\nError during proxy checking: {e}")

if __name__ == "__main__":
    main()
