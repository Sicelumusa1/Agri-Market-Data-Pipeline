#!/usr/bin/env python3
"""
Docker container entry point for Kestra orchestration.
Handles command line arguments and environment variables.
"""
import sys
import os
import json
import logging
from dlt_project.pipeline import MarketDataPipeline

def main():
    # Parse arguments
    if "--full" in sys.argv:
        data_type = None
    elif "--type" in sys.argv:
        try:
            idx = sys.argv.index("--type")
            data_type = sys.argv[idx + 1]
        except IndexError:
            data_type = None
    else:
        data_type = None
    
    # Initialize pipeline
    pipeline = MarketDataPipeline()
    
    # Run pipeline
    if data_type:
        result = pipeline.run_by_data_type(data_type)
    else:
        result = pipeline.run_full_pipeline()
    
    # Output result as JSON (for Kestra)
    print(json.dumps(result, default=str))
    
    # Exit code based on result
    sys.exit(0 if result.get("status") == "success" else 1)

if __name__ == "__main__":
    main()