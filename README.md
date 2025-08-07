# Proxy Scraper and Checker Tools

This package contains three main tools for working with proxies:

## Files

1. **proxy_scraper.py** - Scrapes proxies from websites
2. **proxy_checker.py** - Tests proxy lists for working proxies
3. **proxy_tool.py** - Integrated tool that combines both functions
4. **proxy_sources.txt** - Sample URLs for proxy sources

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Proxy Scraper Only

```bash
python proxy_scraper.py
```

Interactive mode - you'll be prompted to enter URLs or load from file.

### 2. Proxy Checker Only

```bash
python proxy_checker.py
```

Checks proxies in `proxy_list.txt` by default.

### 3. Integrated Tool (Recommended)

```bash
# Interactive mode - prompts you to choose scrape/check/both
python proxy_tool.py

# Scrape and check in one go (automatically uses proxy_sources.txt if no URLs provided)
python proxy_tool.py --mode both

# Scrape only (automatically uses proxy_sources.txt if available)
python proxy_tool.py --mode scrape

# Scrape only with specific URLs
python proxy_tool.py --mode scrape --urls https://example.com/proxies

# Check only
python proxy_tool.py --mode check --proxy-file my_proxies.txt

# Use URLs from file
python proxy_tool.py --mode both --url-file proxy_sources.txt

# Custom settings
python proxy_tool.py --mode both --max-workers 100 --timeout 5 --max-pages 10
```

## Options

- `--mode`: scrape, check, or both
- `--urls`: Space-separated list of URLs to scrape
- `--url-file`: File containing URLs (one per line)
- `--proxy-file`: File containing proxies to check
- `--max-workers`: Number of threads (default: 50)
- `--timeout`: Timeout in seconds (default: 10)
- `--max-pages`: Max pages to scrape per site (default: 5)
- `--delay`: Delay between scraping requests (default: 1)

## Output Files

The tools create the following files:

### Scraper Output
- `proxy_list/proxy_list.txt` - All scraped proxies (no duplicates)
- `proxy_list/scrape_summary_YYYYMMDD_HHMMSS.json` - Scraping statistics

### Checker Output
- `working_http_proxies_YYYYMMDD_HHMMSS.txt`
- `working_https_proxies_YYYYMMDD_HHMMSS.txt`
- `working_socks4_proxies_YYYYMMDD_HHMMSS.txt`
- `working_socks5_proxies_YYYYMMDD_HHMMSS.txt`
- `failed_proxies_YYYYMMDD_HHMMSS.txt`

## Features

### Proxy Scraper
- Automatic pagination detection
- Multithreaded scraping
- Regex-based proxy extraction
- Respectful scraping with delays
- Automatic duplicate removal
- Single output file for easy use

### Proxy Checker
- Tests all proxy types (HTTP/HTTPS/SOCKS4/SOCKS5)
- Multithreaded checking for speed
- Real-time progress display
- Automatic duplicate removal before checking
- Detailed success rate statistics
- Separate output files by type

## Example Workflow

1. **Easy start - Interactive mode:**
   ```bash
   python proxy_tool.py
   ```
   Then choose: 1=Scrape, 2=Check, 3=Both

2. **Scrape proxies from multiple sources (automatically uses proxy_sources.txt):**
   ```bash
   python proxy_tool.py --mode scrape
   ```

3. **Check the scraped proxies:**
   ```bash
   python proxy_tool.py --mode check
   ```

4. **Or do both in one command:**
   ```bash
   python proxy_tool.py --mode both --max-workers 100
   ```

## Tips

- Start with fewer workers (10-20) for scraping to be respectful to websites
- Use more workers (50-100) for checking since it's testing connectivity
- Adjust timeout based on your internet speed and proxy locations
- Some websites may block automated scraping - use delays and rotate User-Agents if needed
- The tools automatically handle duplicates and invalid proxy formats
- Place your proxy source URLs in `proxy_sources.txt` for automatic loading
- The scraper saves to `proxy_list.txt` which the checker automatically uses

## Troubleshooting

- **Import errors**: Run `pip install -r requirements.txt`
- **No proxies found**: Check if URLs are accessible and contain proxy lists
- **Slow checking**: Reduce timeout or increase max-workers
- **Memory issues**: Reduce max-workers or process smaller batches
