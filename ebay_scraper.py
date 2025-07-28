# ebay_price_analyzer.py
#
# Description:
# This script performs an advanced search on eBay for a product. It asks the user for
# a desired price-per-terabyte range and a target number of results. It then searches
# through multiple pages. For listings with multiple variations (e.g., different capacities),
# it visits the product page to extract and analyze each individual option.
# It also generates a detailed log file named 'analysis_log.md' for troubleshooting.
#
# Required libraries:
# You need to install 'requests', 'beautifulsoup4', 'pandas', and 'matplotlib'.
# Open your terminal or command prompt and run:
# pip install requests beautifulsoup4 pandas matplotlib

import requests
import re
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import time
import json
import random

# --- CONFIGURATION ---
# Delay in seconds between each request to eBay's servers to avoid bot detection.
# A value between 2 and 5 is recommended.
DELAY_TIME_BASE = 3
DELAY_BETWEEN_REQUESTS = DELAY_TIME_BASE + random.uniform(0, 2)

def extract_best_capacity(title: str) -> float | None:
    """
    Extracts the most relevant SSD capacity from a product title.
    Prioritizes TB values over GB and returns the largest match.
    """
    # Normalize title (replace slashes/dashes, lowercase)
    normalized = title.replace("/", " ").replace("-", " ").replace("_", " ").lower()

    # Find all GB/TB capacity candidates
    matches = re.findall(r'(\d+\.?\d*)\s*(tb|gb)', normalized)
    if not matches:
        return None

    # Parse matches into float TB values
    tb_values = [float(val) for val, unit in matches if unit == 'tb']
    gb_values = [float(val) / 1000.0 for val, unit in matches if unit == 'gb']

    if tb_values:
        return max(tb_values)
    elif gb_values:
        return max(gb_values)
    return None

def get_user_input():
    """Gets all necessary search criteria from the user."""
    search_term = input("Enter the product to search for on eBay (e.g., 'nvme ssd'): ")
    while not search_term:
        print("Search term cannot be empty.")
        search_term = input("Enter the product to search for on eBay (e.g., 'nvme ssd'): ")

    while True:
        try:
            min_price_tb = float(input("Enter the MINIMUM acceptable price per TB (e.g., 20): "))
            max_price_tb = float(input("Enter the MAXIMUM acceptable price per TB (e.g., 100): "))
            if min_price_tb >= max_price_tb:
                print("Minimum price must be less than maximum price.")
                continue
            desired_results = int(input("Enter the desired number of valid results to find: "))
            return search_term, min_price_tb, max_price_tb, desired_results
        except ValueError:
            print("Invalid input. Please enter valid numbers.")

def fetch_page(url):
    """Fetches the content of a given URL with standard headers."""
    print(f"  > Fetching URL: {url[:75]}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    try:
        # Add a delay before every request to be respectful to the server
        time.sleep(DELAY_BETWEEN_REQUESTS)
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return None

def parse_search_page(html_content):
    """
    Parses the search results page to identify single-price listings and
    multi-variation listings that need further investigation.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = []
    item_container = soup.find('ul', class_=re.compile(r'srp-results'))
    if not item_container:
        return []
    
    items = item_container.find_all('li', class_=re.compile(r's-item'))
    for item in items:
        try:
            title_element = item.find('div', class_=re.compile(r's-item__title'))
            # Sometimes the title is inside an H3 tag
            if not title_element:
                title_element = item.find('h3', class_=re.compile(r's-item__title'))
            title = title_element.text.strip() if title_element else 'N/A'
            
            price_element = item.find('span', class_=re.compile(r's-item__price'))
            price_str = price_element.text.strip() if price_element else 'N/A'
            
            url_element = item.find('a', class_=re.compile(r's-item__link'))
            url = url_element['href'] if url_element else 'N/A'

            if url == 'N/A' or title == 'N/A':
                continue

            # If price is a range, it's a multi-variation listing.
            if 'to' in price_str.lower():
                listings.append({'title': title, 'url': url, 'is_multi_variation': True})
            else:
                listings.append({'title': title, 'price_str': price_str, 'url': url, 'is_multi_variation': False})
        except Exception:
            continue
    return listings

def parse_variations_from_product_page(html_content, base_title):
    """
    Parses an individual product page to extract all variations (e.g., capacities and prices).
    It looks for a JSON object embedded in a <script> tag.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    processed_listings = []
    
    # Find the script tag containing variation data. This is a common eBay pattern.
    scripts = soup.find_all('script', type='text/javascript')
    variation_data = None
    for script in scripts:
        if script.string and 'msku.JsonModel' in script.string:
            # Extract the JSON part from the script
            json_str_match = re.search(r'msku\.JsonModel\s*=\s*(\{.*?\});', script.string)
            if json_str_match:
                try:
                    variation_data = json.loads(json_str_match.group(1))
                    break
                except json.JSONDecodeError:
                    continue

    if not variation_data or 'menu' not in variation_data:
        return []

    # Iterate through all combinations of variations
    for item_id, details in variation_data.get('menu', {}).items():
        try:
            # Construct a full title from the base title and variation details
            variation_title = " ".join(val['valueName'] for val in details['propVals'].values())
            full_title = f"{base_title} - {variation_title}"
            
            price = details.get('price', {}).get('value')
            if not price:
                continue

            # Now analyze this specific variation
            capacity_tb = extract_best_capacity(full_title)
            if not capacity_tb:
                continue

            value_str, unit = match.groups()
            capacity_tb = float(value_str) if unit.upper() == 'TB' else float(value_str) / 1000.0
            
            if capacity_tb > 0:
                price_per_tb = float(price) / capacity_tb
                processed_listings.append({
                    'title': full_title,
                    'price_usd': float(price),
                    'capacity_tb': capacity_tb,
                    'price_per_tb': price_per_tb,
                    'url': '' # URL is not needed for individual variations
                })
        except (KeyError, TypeError):
            continue
            
    return processed_listings


def calculate_price_per_tb(listing):
    """Processes a single-price listing to calculate the price per terabyte."""
    capacity_tb = extract_best_capacity(listing['title'])
    if not capacity_tb or capacity_tb <= 0:
        return None

    price_match = re.search(r'\d{1,3}(?:,?\d{3})*(?:\.\d{2})?', listing['price_str'])
    if not price_match:
        return None

    price = float(price_match.group(0).replace(',', ''))

    listing['price_usd'] = price
    listing['capacity_tb'] = capacity_tb
    listing['price_per_tb'] = price / capacity_tb
    return listing

def plot_results(listings_df, min_price_tb, max_price_tb):
    """Displays two graphs based on the final, filtered results."""
    if listings_df.empty:
        print("No data available to plot.")
        return

    plt.style.use('seaborn-v0_8-whitegrid')

    # --- Graph 1: Bar Chart of Top Deals ---
    plot_data_bar = listings_df.head(20).sort_values('price_per_tb', ascending=False)
    short_titles = [f"{title[:40]}..." if len(title) > 40 else title for title in plot_data_bar['title']]
    
    fig1, ax1 = plt.subplots(figsize=(12, 10))
    bars = ax1.barh(short_titles, plot_data_bar['price_per_tb'], color='c')
    ax1.set_xlabel('Price per TB ($)')
    ax1.set_ylabel('SSD Listing')
    ax1.set_title(f'Top {len(plot_data_bar)} SSD Deals Found in Price Range')
    
    for bar in bars:
        width = bar.get_width()
        ax1.text(width - 1, bar.get_y() + bar.get_height()/2, f'${width:.2f}', ha='right', va='center', color='white', weight='bold')
    fig1.tight_layout()

    # --- Graph 2: Scatter Plot with User-Defined Color Range ---
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    scatter = ax2.scatter(
        listings_df['capacity_tb'], 
        listings_df['price_usd'], 
        c=listings_df['price_per_tb'], 
        cmap='viridis_r',
        alpha=0.7,
        s=100,
        vmin=min_price_tb,
        vmax=max_price_tb
    )
    ax2.set_xlabel('Capacity (TB)')
    ax2.set_ylabel('Price (USD)')
    ax2.set_title('SSD Price vs. Capacity Overview (Filtered Results)')
    
    cbar = fig2.colorbar(scatter)
    cbar.set_label('Price per TB ($)')
    ax2.grid(True)
    fig2.tight_layout()

    print("\nDisplaying graphs. Close the graph windows to exit the script.")
    plt.show()

def main():
    """Main function to orchestrate the search and analysis."""
    search_term, min_price_tb, max_price_tb, desired_results = get_user_input()
    
    log_filename = "analysis_log.md"
    print(f"\nLogging detailed analysis to '{log_filename}'...")

    with open(log_filename, "w", encoding="utf-8") as log_file:
        log_file.write(f"# eBay SSD Analysis Log for '{search_term}'\n\n")
        log_file.write(f"**Search Criteria:**\n")
        log_file.write(f"- Price/TB Range: ${min_price_tb:.2f} to ${max_price_tb:.2f}\n")
        log_file.write(f"- Desired Results: {desired_results}\n\n")
        log_file.write("| Status | Type | Title | Price/TB |\n")
        log_file.write("|:---|:---|:---|:---|\n")

        all_analyzed_listings = []
        valid_listings = []
        page_number = 1
        consecutive_empty_pages = 0
        EMPTY_PAGE_LIMIT = 5
        
        print("\n--- Starting Search ---")
        # Loop until we find the desired number of VALID results
        while len(valid_listings) < desired_results:
            search_url = f"https://www.ebay.com/sch/i.html?_nkw={'+'.join(search_term.split())}&_sop=15&_pgn={page_number}"
            print(f"Searching page {page_number}...")
            log_file.write(f"\n*Parsing Page {page_number}*\n\n")
            search_html = fetch_page(search_url)
            if not search_html:
                print("Failed to retrieve search page, stopping.")
                break
            
            listings_on_page = parse_search_page(search_html)
            if not listings_on_page:
                consecutive_empty_pages += 1
                print(f"No listings found on page {page_number}. (Empty page count: {consecutive_empty_pages}/{EMPTY_PAGE_LIMIT})")
                log_file.write("| INFO | System | No listings found on this page. |\n")
                if consecutive_empty_pages >= EMPTY_PAGE_LIMIT:
                    print("Reached consecutive empty page limit, stopping search.")
                    break
                page_number += 1
                continue
            
            consecutive_empty_pages = 0

            for listing in listings_on_page:
                if listing['is_multi_variation']:
                    print(f"  -> Found multi-variation listing: {listing['title'][:50]}...")
                    product_html = fetch_page(listing['url'])
                    if product_html:
                        variations = parse_variations_from_product_page(product_html, listing['title'])
                        if variations:
                            print(f"     ...Found {len(variations)} variations.")
                            for v in variations:
                                log_file.write(f"| SUCCESS | Variation | `{v['title']}` | **${v['price_per_tb']:.2f}** |\n")
                            all_analyzed_listings.extend(variations)
                        else:
                            print("     ...Could not extract variations from page.")
                            log_file.write(f"| SKIPPED | Multi | *{listing['title'][:80]}...* | Could not extract |\n")
                else:
                    analyzed = calculate_price_per_tb(listing)
                    if analyzed:
                        log_file.write(f"| SUCCESS | Single | `{analyzed['title']}` | **${analyzed['price_per_tb']:.2f}** |\n")
                        all_analyzed_listings.append(analyzed)
                    else:
                        log_file.write(f"| SKIPPED | Single | `{listing['title']}` | N/A (no capacity/price) |\n")
            
            # After processing a page, update the list of valid listings
            valid_listings = [l for l in all_analyzed_listings if min_price_tb <= l['price_per_tb'] <= max_price_tb]
            print(f"Total valid results so far: {len(valid_listings)}/{desired_results}")
            
            if len(valid_listings) >= desired_results:
                print("Found desired number of valid results. Stopping search.")
                break

            page_number += 1

    if not all_analyzed_listings:
        print("\nCould not find any listings at all.")
        return
    
    if not valid_listings:
        print("\nFound listings, but none matched your price-per-TB criteria.")
        return

    sorted_listings = sorted(valid_listings, key=lambda x: x['price_per_tb'])
    results_df = pd.DataFrame(sorted_listings)
    
    display_df = results_df.copy()
    display_df['price_usd'] = display_df['price_usd'].map('${:,.2f}'.format)
    display_df['capacity_tb'] = display_df['capacity_tb'].map('{:.2f} TB'.format)
    display_df['price_per_tb'] = display_df['price_per_tb'].map('${:,.2f}'.format)
    final_display_df = display_df[['title', 'price_usd', 'capacity_tb', 'price_per_tb', 'url']]

    print(f"\n--- Found {len(results_df)} SSDs Matching Your Criteria ---")
    print(final_display_df.to_string())

    plot_results(results_df, min_price_tb, max_price_tb)

if __name__ == "__main__":
    main()
