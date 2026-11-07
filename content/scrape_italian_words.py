#!/usr/bin/env python3
"""
Scrape the most common Italian words from Wiktionary frequency list
and save them as a CSV or Parquet file.

Usage:
    python3 scrape_italian_words.py [--parquet] [output_file]

Examples:
    python3 scrape_italian_words.py
        -> Saves to italian_words_frequency.csv
    
    python3 scrape_italian_words.py --parquet
        -> Attempts to save as .parquet, falls back to .csv
    
    python3 scrape_italian_words.py my_words.csv
        -> Saves to my_words.csv
    
    python3 scrape_italian_words.py --parquet my_words.parquet
        -> Saves to my_words.parquet (or .csv if pyarrow unavailable)
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# URL to scrape
WIKTIONARY_URL = "https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Italian1000"
DEFAULT_OUTPUT = "italian_words_frequency.csv"


def scrape_italian_words(url=WIKTIONARY_URL):
    """
    Scrape the Italian word frequency list from Wiktionary.
    
    Returns:
        list: List of dicts with keys [rank, word, frequency]
    """
    print(f"Fetching {url}...")
    
    # Fetch the page with User-Agent header (Wiktionary blocks requests without it)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        sys.exit(1)
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main table (wikitable sortable)
    table = soup.find('table', {'class': 'wikitable sortable'})
    
    if not table:
        print("Error: Could not find frequency table on the page")
        sys.exit(1)
    
    # Extract rows
    rows = table.find_all('tr')
    print(f"Found {len(rows)} rows in table (including header)")
    
    # Parse table data
    data = []
    for row in rows[1:]:  # Skip header row
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 3:
            try:
                # Extract text from cells
                rank_text = cells[0].get_text().strip().rstrip('.')
                word_text = cells[1].get_text().strip()
                freq_text = cells[2].get_text().strip()
                
                # Skip empty rows
                if not rank_text or not word_text or not freq_text:
                    continue
                
                rank = int(rank_text)
                word = word_text
                frequency = int(freq_text.replace(',', ''))  # Handle comma-separated numbers
                
                data.append({
                    'rank': rank,
                    'word': word,
                    'frequency': frequency
                })
            except (ValueError, IndexError, AttributeError) as e:
                # Skip rows that can't be parsed
                continue
    
    print(f"\nSuccessfully parsed {len(data)} word entries")
    print("\nFirst 5 entries:")
    for row in data[:5]:
        print(f"  {row}")
    
    return data


def save_to_parquet(data, output_path):
    """
    Save list of dicts to parquet file.
    
    First tries pyarrow, falls back to CSV if pyarrow is unavailable.
    
    Args:
        data (list): List of dictionaries with keys [rank, word, frequency]
        output_path (str or Path): Path where to save the file
    """
    output_path = Path(output_path)
    
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try using pyarrow
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        
        # Convert to pyarrow table
        table = pa.table({
            'rank': [row['rank'] for row in data],
            'word': [row['word'] for row in data],
            'frequency': [row['frequency'] for row in data]
        })
        
        # Write parquet file
        pq.write_table(table, output_path, compression='snappy')
        print(f"\n✓ Successfully saved to {output_path} (parquet format)")
        print(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
        print(f"  Records: {len(data)}")
        print(f"  Format: parquet")
        
    except ImportError:
        # Fallback to CSV format
        import csv
        
        output_path = output_path.with_suffix('.csv')
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['rank', 'word', 'frequency'])
                writer.writeheader()
                writer.writerows(data)
            
            print(f"\n⚠ PyArrow not available, saved as CSV instead:")
            print(f"  Path: {output_path}")
            print(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
            print(f"  Records: {len(data)}")
            print(f"  Format: CSV")
            print(f"\n  To convert to Parquet later, install pyarrow:")
            print(f"    pip install pyarrow")
            
        except Exception as e:
            print(f"Error saving CSV file: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    # Parse command line arguments
    args = sys.argv[1:]
    use_parquet = False
    output_file = DEFAULT_OUTPUT
    
    # Check for --parquet flag
    if '--parquet' in args:
        use_parquet = True
        args.remove('--parquet')
    
    # Get output filename if provided
    if args:
        output_file = args[0]
    elif use_parquet:
        output_file = DEFAULT_OUTPUT.replace('.csv', '.parquet')
    
    print("=" * 60)
    print("Italian Word Frequency Scraper")
    print("=" * 60)
    
    # Scrape the data
    data = scrape_italian_words()
    
    # Save to CSV or Parquet
    if use_parquet:
        output_path = Path(output_file)
        if output_path.suffix != '.parquet':
            output_file = str(output_path.with_suffix('.parquet'))
    
    save_to_parquet(data, output_file)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
