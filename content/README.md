# Italian Word Frequency List

This folder contains scripts to scrape and convert the most common Italian words from the Wiktionary frequency list.

## Contents

- **`scrape_italian_words.py`** - Main scraping script
- **`csv_to_parquet.py`** - Utility to convert CSV to Parquet format
- **`italian_words_frequency.csv`** - The scraped data (1000 most common Italian words)

## Data Source

The data is scraped from:
https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Italian1000

This list contains the 1000 most common Italian words, generated from subtitles of movies and television series with a total of about 5.6 million words (as of 2008).

## Quick Start

### Get the data (CSV format)

```bash
python3 scrape_italian_words.py
```

This will create `italian_words_frequency.csv` with columns:
- `rank`: Word frequency rank (1-1000)
- `word`: The Italian word
- `frequency`: Frequency count (occurrences per million - ppm)

### Convert to Parquet format

If you have `pyarrow` installed:

```bash
# Scrape directly to Parquet
python3 scrape_italian_words.py --parquet

# Or convert existing CSV to Parquet
python3 csv_to_parquet.py italian_words_frequency.csv italian_words_frequency.parquet
```

## Detailed Usage

### scrape_italian_words.py

```bash
# Default: saves to italian_words_frequency.csv
python3 scrape_italian_words.py

# Save to custom CSV file
python3 scrape_italian_words.py my_words.csv

# Try to save as Parquet (falls back to CSV if pyarrow not available)
python3 scrape_italian_words.py --parquet

# Save to custom Parquet file
python3 scrape_italian_words.py --parquet my_words.parquet
```

### csv_to_parquet.py

```bash
# Convert CSV to Parquet with auto-generated output name
python3 csv_to_parquet.py italian_words_frequency.csv

# Convert to specific Parquet file
python3 csv_to_parquet.py italian_words_frequency.csv output.parquet
```

## Data Format

### CSV Format
```
rank,word,frequency
1,non,25757
2,di,22868
3,che,22738
4,è,18624
5,e,17600
...
1000,giuro,98
```

### Parquet Format
Same data structure as CSV, but stored in columnar Apache Parquet format for better compression and query performance.

## Requirements

### For scraping (CSV output)
- Python 3.6+
- `requests` - HTTP library
- `beautifulsoup4` - HTML parsing

Both are commonly available. Check with:
```bash
python3 -c "import requests; import bs4; print('✓ Dependencies available')"
```

### For Parquet output
- `pyarrow` - Apache Arrow library for Parquet support

Install with:
```bash
pip install pyarrow
```

## Integration with Italian Tutor

To use this data with the Italian Tutor application:

```python
import pandas as pd

# Load the frequency list
df = pd.read_csv('italian_words_frequency.csv')

# Get top 100 words
top_100 = df.head(100)['word'].tolist()

# Filter words by proficiency level
beginner_words = df[df['rank'] <= 500]['word'].tolist()
```

## Notes

- The frequency counts are based on movies/TV subtitles from 2008
- All words were split after apostrophes and converted to lowercase before counting
- A complete list with all words having at least 2 occurrences is available at:
  https://en.wiktionary.org/wiki/User:Matthias_Buchmeier#Italian_frequency_list

## Performance Notes

- Scraping typically takes 10-30 seconds (depends on network speed)
- CSV file size: ~15 KB
- Parquet file size: ~8-10 KB (with snappy compression)

## Troubleshooting

**"Error: Could not find frequency table on the page"**
- The Wiktionary page structure may have changed
- Check the URL in the script is still valid

**"403 Client Error: Forbidden"**
- The User-Agent header might be blocked
- Try updating the User-Agent string in `scrape_italian_words.py`

**"ModuleNotFoundError: No module named 'requests' or 'bs4'"**
- Install missing dependencies:
  ```bash
  pip install requests beautifulsoup4
  ```

**Parquet not available**
- Install pyarrow: `pip install pyarrow`
- Or just use CSV format as-is

## License

The data comes from Wiktionary (https://www.wiktionary.org/), which is released under the Creative Commons Attribution-ShareAlike License.
