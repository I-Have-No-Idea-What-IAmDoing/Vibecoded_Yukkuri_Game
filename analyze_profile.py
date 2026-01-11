import pstats
import sys

def analyze(filename):
    p = pstats.Stats(filename)
    p.strip_dirs()
    print("--- Top 20 by Cumulative Time ---")
    p.sort_stats('cumulative').print_stats(20)
    print("\n--- Top 20 by Total Time ---")
    p.sort_stats('tottime').print_stats(20)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
    else:
        print("Usage: python analyze_profile.py <stats_file>")
