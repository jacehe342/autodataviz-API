# Main Entrance
import os
import sys
import uvicorn

# Always insert the project directory into sys.path before importing local packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from web.main_web import web
except ImportError as e:
    # Print clear details if loading fails
    print(f'FILE ERROR!!! Details: {e}')
    raise e

if __name__ == '__main__':
    uvicorn.run(web)