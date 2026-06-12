import os
import subprocess
import shutil
from PIL import Image

def generate_tauri_icons(src_image_path, dest_dir):
    print(f"Opening source image: {src_image_path}")
    if not os.path.exists(src_image_path):
        print(f"Error: Source image {src_image_path} does not exist.")
        return False
        
    os.makedirs(dest_dir, exist_ok=True)
    img = Image.open(src_image_path)
    
    # Explicitly convert to RGBA (Red, Green, Blue, Alpha) as required by Tauri
    img_rgba = img.convert("RGBA")
    
    # 1. Generate standard PNGs
    print("Generating PNG sizes (RGBA)...")
    img_rgba.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(dest_dir, "32x32.png"), "PNG")
    img_rgba.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(dest_dir, "128x128.png"), "PNG")
    img_rgba.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(dest_dir, "128x128@2x.png"), "PNG")
    
    # 2. Generate ICO file
    print("Generating icon.ico...")
    img_rgba.resize((256, 256), Image.Resampling.LANCZOS).save(
        os.path.join(dest_dir, "icon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    
    # 3. Generate ICNS file using macOS iconutil
    print("Generating icon.icns...")
    iconset_dir = os.path.join(dest_dir, "icon.iconset")
    os.makedirs(iconset_dir, exist_ok=True)
    
    sizes = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    
    for filename, size in sizes:
        img_rgba.resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(iconset_dir, filename), "PNG")
        
    try:
        icns_path = os.path.join(dest_dir, "icon.icns")
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path], check=True)
        print("Successfully generated icon.icns using iconutil.")
    except Exception as e:
        print(f"iconutil failed ({e}), falling back to PIL ICNS save...")
        try:
            img_rgba.resize((512, 512), Image.Resampling.LANCZOS).save(icns_path, format="ICNS")
            print("Successfully generated icon.icns using PIL fallback.")
        except Exception as pil_e:
            print(f"PIL fallback also failed: {pil_e}")
    finally:
        shutil.rmtree(iconset_dir, ignore_errors=True)

    print("All icons successfully generated in RGBA mode.")
    return True

if __name__ == "__main__":
    src = "/Users/ashishpaliwal/apps/ErgoLearn AI/src-frontend/app-icon.png"
    dest = "/Users/ashishpaliwal/apps/ErgoLearn AI/src-tauri/icons"
    generate_tauri_icons(src, dest)
