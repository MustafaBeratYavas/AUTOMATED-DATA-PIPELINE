# -- Project Root Path Resolution --
# Anchors the absolute project root by traversing two levels up from this file.
# All downstream modules reference ROOT_DIR for deterministic path construction.

import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
