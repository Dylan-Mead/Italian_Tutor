#!/usr/bin/env python3
"""
Example script showing how to integrate the Italian word frequency list
with the Italian Tutor application.

This script demonstrates various ways to use the frequency data for
filtering vocabulary by proficiency level.
"""

import csv
from pathlib import Path


def load_frequency_list(csv_file='italian_words_frequency.csv'):
    """
    Load the Italian word frequency list from CSV.
    
    Returns:
        dict: Mapping of word -> frequency data
        list: List of (word, frequency, rank) sorted by rank
    """
    csv_path = Path(__file__).parent / csv_file
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    words_dict = {}
    words_list = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row['word']
            rank = int(row['rank'])
            frequency = int(row['frequency'])
            
            words_dict[word] = {
                'rank': rank,
                'frequency': frequency
            }
            words_list.append((word, frequency, rank))
    
    return words_dict, words_list


def get_vocabulary_by_level(words_dict, proficiency_level):
    """
    Get vocabulary appropriate for a given proficiency level.
    
    Args:
        words_dict: Dictionary from load_frequency_list()
        proficiency_level: CEFR level (A1, A2, B1, B2, C1, C2)
    
    Returns:
        list: Words appropriate for the level
    """
    # Approximate CEFR proficiency cutoffs based on frequency
    # These are rough estimates and should be tuned based on actual proficiency
    levels = {
        'A1': 200,    # Top 200 most common words
        'A2': 500,    # Top 500 words
        'B1': 1000,   # Top 1000 words
        'B2': 1500,   # Beyond our list, but extrapolate
        'C1': 3000,
        'C2': 5000
    }
    
    if proficiency_level not in levels:
        raise ValueError(f"Unknown proficiency level: {proficiency_level}")
    
    max_rank = levels[proficiency_level]
    return [
        word for word, data in words_dict.items()
        if data['rank'] <= max_rank
    ]


def get_words_by_rank_range(words_dict, start_rank=1, end_rank=100):
    """
    Get words within a specific rank range.
    
    Args:
        words_dict: Dictionary from load_frequency_list()
        start_rank: Starting rank (inclusive)
        end_rank: Ending rank (inclusive)
    
    Returns:
        list: Words in the specified rank range
    """
    return [
        word for word, data in words_dict.items()
        if start_rank <= data['rank'] <= end_rank
    ]


def get_frequency_statistics(words_list):
    """
    Print statistics about the frequency distribution.
    
    Args:
        words_list: List from load_frequency_list()
    """
    if not words_list:
        return
    
    frequencies = [f for _, f, _ in words_list]
    
    print("Frequency List Statistics")
    print("=" * 50)
    print(f"Total words: {len(words_list)}")
    print(f"Most frequent word: {frequencies[0]} occurrences (ppm)")
    print(f"Least frequent word: {frequencies[-1]} occurrences (ppm)")
    print(f"Average frequency: {sum(frequencies) / len(frequencies):.0f} (ppm)")
    print()


def main():
    """Demonstrate the frequency list usage."""
    
    # Load the data
    print("Loading Italian word frequency list...")
    words_dict, words_list = load_frequency_list()
    
    # Show statistics
    get_frequency_statistics(words_list)
    
    # Example 1: Get top 50 words
    print("\nExample 1: Top 50 most common words")
    print("-" * 50)
    top_50 = get_words_by_rank_range(words_dict, 1, 50)
    print(f"Count: {len(top_50)}")
    print(f"Words: {', '.join(top_50[:10])}...")
    print()
    
    # Example 2: Words by proficiency level
    print("Example 2: Vocabulary by CEFR proficiency level")
    print("-" * 50)
    for level in ['A1', 'A2', 'B1']:
        vocab = get_vocabulary_by_level(words_dict, level)
        print(f"{level}: {len(vocab)} words")
    print()
    
    # Example 3: Lookup a word's frequency
    print("Example 3: Word frequency lookup")
    print("-" * 50)
    test_words = ['ciao', 'amore', 'gatto', 'casa']
    for word in test_words:
        if word in words_dict:
            data = words_dict[word]
            print(f"'{word}': rank {data['rank']}, frequency {data['frequency']} ppm")
        else:
            print(f"'{word}': not in top 1000")
    print()
    
    # Example 4: Get a range of words (for exercises)
    print("Example 4: Intermediate vocabulary (ranks 300-400)")
    print("-" * 50)
    intermediate = get_words_by_rank_range(words_dict, 300, 400)
    print(f"Count: {len(intermediate)}")
    print(f"Words: {', '.join(intermediate[:15])}...")
    print()


if __name__ == '__main__':
    main()
