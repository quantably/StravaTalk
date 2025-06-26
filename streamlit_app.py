#!/usr/bin/env python3
"""
Entry point for Streamlit application that sets up the proper module path.
"""

import sys
import os

# Add the current directory to Python path so stravatalk package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the actual Streamlit app
from stravatalk.app import *