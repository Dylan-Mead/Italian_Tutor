#!/usr/bin/env python3
"""
Convert CSV word frequency file to Parquet format.

Usage:
    python3 csv_to_parquet.py input.csv [output.parquet]
"""

import sys
from pathlib import Path


def csv_to_parquet(csv_path, parquet_path=None):
    """
    Convert CSV file to Parquet format using pyarrow.
    
    Args:
        csv_path (str or Path): Path to CSV file
        parquet_path (str or Path): Path to output parquet file (default: same name, .parquet extension)
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    if parquet_path is None:
        parquet_path = csv_path.with_suffix('.parquet')
    else:
        parquet_path = Path(parquet_path)
    
    try:
        import pyarrow.csv as csv_module
        import pyarrow.parquet as pq
    except ImportError:
        print("Error: pyarrow is not installed.")
        print("Install it with: pip install pyarrow")
        sys.exit(1)
    
    try:
        print(f"Reading CSV from {csv_path}...")
        table = csv_module.read_csv(csv_path)
        print(f"  Records: {len(table)}")
        print(f"  Columns: {table.column_names}")
        
        print(f"\nWriting Parquet to {parquet_path}...")
        pq.write_table(table, parquet_path, compression='snappy')
        
        file_size_kb = parquet_path.stat().st_size / 1024
        print(f"✓ Successfully converted!")
        print(f"  Output file size: {file_size_kb:.2f} KB")
        print(f"  Compression: snappy")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 csv_to_parquet.py input.csv [output.parquet]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    parquet_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    csv_to_parquet(csv_file, parquet_file)
