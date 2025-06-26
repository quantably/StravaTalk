#!/usr/bin/env python3
"""
Entry point for Streamlit application that sets up the proper module path.
"""

import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("🚀 Starting StravaTalk Streamlit application...")

# Add the current directory to Python path so stravatalk package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logger.info(f"✅ Added to Python path: {os.path.dirname(os.path.abspath(__file__))}")

try:
    logger.info("📦 Importing stravatalk.app module...")
    # Import the app module
    import stravatalk.app
    logger.info("✅ Successfully imported stravatalk.app")
    
    # Actually run the Streamlit app
    logger.info("🚀 Calling main() to start Streamlit interface...")
    stravatalk.app.main()
    logger.info("✅ Streamlit app main() completed")
    
except Exception as e:
    logger.error(f"❌ Failed to run stravatalk.app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise

logger.info("🎉 StravaTalk app entry point completed!")