import cv2
import sys

def scan_cameras(max_indices=5):
    print("Scanning for available camera indexes...")
    found_any = False
    
    for index in range(max_indices):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w, c = frame.shape
                print(f"Index {index}: SUCCESS (Opened successfully. Frame size: {w}x{h})")
                found_any = True
            else:
                print(f"Index {index}: WARNING (Opened, but failed to read frame)")
            cap.release()
        else:
            print(f"Index {index}: FAILED (Could not open)")
            
    if not found_any:
        print("\n[ERROR] No cameras could be opened.")
        print("This typically happens on macOS if the terminal run environment does not have Camera Permissions.")
        print("Please check: System Settings -> Privacy & Security -> Camera, and ensure your terminal app (Terminal/iTerm/VSCode) is checked.")
        sys.exit(1)
    else:
        print("\nScan completed.")

if __name__ == "__main__":
    scan_cameras()
