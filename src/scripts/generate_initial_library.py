import sys
import os
# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.agent import skill_library
import os

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Save the current library (which has been initialized in src.agent)
skill_library.save_to_json('src/data/initial_skill_library.json')
print("Initial skill library saved to src/data/initial_skill_library.json")
