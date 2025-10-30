#!/usr/bin/env python3

import sys
from pathlib import Path
from rembg import remove
from PIL import Image

if len(sys.argv) != 2:
    print("Usage: nukki.py <input_image>")
    print("Output will be saved as <input_image>_nukki.png")
    sys.exit(1)

input_path = Path(sys.argv[1])

if not input_path.exists():
    print(f"Error: {input_path} does not exist")
    sys.exit(1)

# Generate output filename
output_path = input_path.parent / f"{input_path.stem}_nukki.png"

print(f"Removing background from {input_path}...")

# Load image
input_img = Image.open(input_path)

# Remove background
output_img = remove(input_img)

# Save result
output_img.save(output_path)

print(f"Saved to {output_path}")
