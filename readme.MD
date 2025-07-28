# 🔍 eBay SSD scraper and price analyzer

A Python-based web scraping tool that searches eBay for SSDs (Solid State Drives), extracts and analyzes their capacity and price data, and helps identify the best deals by calculating **price per terabyte (USD/TB)**.

---

## 📌 Features

- ✅ Searches eBay for user-defined keywords (e.g. "nvme ssd")
- ✅ Supports filtering by **price-per-terabyte** range
- ✅ Extracts price and storage capacity from titles and variation listings
- ✅ Handles both **single-price** and **multi-variation** listings
- ✅ Automatically parses multiple eBay result pages
- ✅ Calculates price-per-TB from listing titles
- ✅ Robust regex engine for messy capacity descriptions (e.g. `"2TB/1TB SSD"`)
- ✅ Plots two interactive graphs:
  - Horizontal bar chart of best deals
  - Price vs capacity scatter plot
- ✅ Generates markdown log (`analysis_log.md`) for inspection/debugging

---

## 🧠 How It Works

1. You enter a product keyword, minimum/maximum `$/TB` range, and number of desired results.
2. The script fetches search results from eBay and parses:
   - Listing title
   - Price (from visible text)
   - Storage capacity (using regex and heuristics)
3. If the listing includes multiple options (e.g., 1TB, 2TB, 4TB), it visits the product page and parses embedded variation data.
4. Results are ranked by **price per terabyte** and visualized.

---

## 🖥️ Installation

### 🔧 Requirements

- Python 3.8+
- pip (Python package manager)

### 📦 Install Dependencies

```bash
pip install requests beautifulsoup4 pandas matplotlib
```

## 🚀 Usage
🏁 Run the script
```bash
python ebay_scraper.py
```
👨‍💻 Example input
```bash
Enter the product to search for on eBay (e.g., 'nvme ssd'): nvme ssd
Enter the MINIMUM acceptable price per TB (e.g., 20): 30
Enter the MAXIMUM acceptable price per TB (e.g., 100): 80
Enter the desired number of valid results to find: 10
```
### 📈 Output

    Console: printed summary of listings and live progress

    Graphical plots:

        Price/TB bar chart

        Price vs Capacity scatter plot

    Log file: analysis_log.md
[![Figure-1.png](https://i.postimg.cc/BQy33Wrp/Figure-1.png)](https://postimg.cc/xcKhGZTN)

[![Figure-2.png](https://i.postimg.cc/Y2sZG6dq/Figure-2.png)](https://postimg.cc/Z06VXdk1)
### 📊 Output Graphs

    Bar Chart: Top SSDs sorted by price-per-terabyte.

    Scatter Plot: Plots SSDs by price (Y) and capacity (X), color-coded by $/TB.

## 🧠 Capacity Detection Logic

The script intelligently parses capacity from listing titles using a regex engine:

Matches: "1TB", "2TB", "500GB", etc.
Supports: "1TB/2TB", "2 TB", "500GB + 1TB", "256gb", etc.

Priority:

    Prefer largest TB match if available

    Else use GB converted to TB

    Filters out irrelevant numbers (e.g., USB sticks)

## 🧪 Troubleshooting
| Issue                                    | Solution                                                        |
| ---------------------------------------- | --------------------------------------------------------------- |
| `Could not extract variations from page` | eBay may have changed their JS structure or variation container |
| Missing prices                           | Some listings are "auction only" or include price ranges        |
| `No listings found`                      | Check search keyword and if eBay blocked your IP                |
| Script exits early                       | Empty page threshold hit or network issue                       |

## 🤝 Contributing

Pull requests are welcome!


## 📄 License

This project is licensed under the MIT License.
