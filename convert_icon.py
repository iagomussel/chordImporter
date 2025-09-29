#!/usr/bin/env python3
"""
Convert SVG icon to ICO format for Windows executable
"""

import os
import sys
from pathlib import Path

def convert_svg_to_ico():
    """Convert SVG to ICO format with multiple sizes."""
    
    # Check if required libraries are available
    try:
        from PIL import Image
        import cairosvg
        print("SUCCESS: Required libraries available")
    except ImportError as e:
        print(f"❌ Missing required library: {e}")
        print("Install with: pip install Pillow cairosvg")
        return False
    
    # Input and output paths
    svg_path = Path("icon.svg")
    ico_path = Path("icon.ico")
    
    if not svg_path.exists():
        print(f"ERROR: SVG file not found: {svg_path}")
        return False
    
    print(f"Converting {svg_path} to {ico_path}")
    
    # Icon sizes for Windows ICO format
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    
    try:
        for size in sizes:
            print(f"  Generating {size}x{size} image...")
            
            # Convert SVG to PNG at specific size
            png_data = cairosvg.svg2png(
                url=str(svg_path),
                output_width=size,
                output_height=size
            )
            
            # Create PIL Image from PNG data
            from io import BytesIO
            image = Image.open(BytesIO(png_data))
            
            # Ensure RGBA mode for transparency
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            images.append(image)
        
        # Save as ICO with multiple sizes
        print(f"Saving ICO file with {len(images)} sizes...")
        images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
        print(f"SUCCESS: Successfully created {ico_path}")
        print(f"File size: {ico_path.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error during conversion: {e}")
        return False

def create_simple_ico_fallback():
    """Create a simple ICO file if SVG conversion fails."""
    try:
        from PIL import Image, ImageDraw
        print("Creating fallback ICO...")
        
        # Create a simple icon with PIL
        size = 256
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Background circle
        margin = 20
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=(33, 150, 243, 255), outline=(21, 101, 192, 255), width=4)
        
        # Musical note (simplified)
        note_x, note_y = size//2 - 20, size//2
        # Note head
        draw.ellipse([note_x-10, note_y-5, note_x+10, note_y+15], fill=(255, 213, 79, 255))
        # Note stem
        draw.rectangle([note_x+8, note_y-40, note_x+12, note_y+5], fill=(255, 213, 79, 255))
        
        # Save multiple sizes
        sizes = [16, 24, 32, 48, 64, 128, 256]
        images = []
        
        for s in sizes:
            resized = image.resize((s, s), Image.Resampling.LANCZOS)
            images.append(resized)
        
        ico_path = Path("icon.ico")
        images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
        print(f"SUCCESS: Fallback ICO created: {ico_path}")
        return True
        
    except Exception as e:
        print(f"ERROR: Fallback creation failed: {e}")
        return False

if __name__ == "__main__":
    print("Musical Tools Suite - Icon Converter")
    print("=" * 50)
    
    # Try SVG conversion first
    success = convert_svg_to_ico()
    
    # If SVG conversion fails, create simple fallback
    if not success:
        print("\nTrying fallback method...")
        success = create_simple_ico_fallback()
    
    if success:
        print("\nSUCCESS: Icon conversion completed successfully!")
        print("Next steps:")
        print("   1. Update ChordImporter.spec to use icon.ico")
        print("   2. Rebuild executable with PyInstaller")
    else:
        print("\nERROR: Icon conversion failed!")
        print("You can:")
        print("   1. Install missing dependencies")
        print("   2. Use an online SVG to ICO converter")
        print("   3. Create icon manually")
