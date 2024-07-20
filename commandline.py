import argparse
import sys
from pathlib import Path

parser = argparse.ArgumentParser(
        prog=Path(sys.argv[0]).stem,
        description='Configure wax.')

parser.add_argument('-p', '--preserve', action='store_true',
        help='do not delete checkpoints when starting')

args = parser.parse_args()

