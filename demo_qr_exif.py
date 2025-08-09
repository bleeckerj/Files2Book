import json
from qr_code_generator import create_qr_code

# Example EXIF metadata dictionary
exif_metadata = {
    "Make": "Canon",
    "Model": "EOS 5D Mark IV",
    "DateTimeOriginal": "2025:08:08 22:32:04",
    "ExposureTime": "1/200",
    "FNumber": "2.8",
    "ISOSpeedRatings": 100,
    "FocalLength": "50.0 mm",
    "GPSLatitude": "34.0522 N",
    "GPSLongitude": "118.2437 W",
    "LensModel": "EF50mm f/1.8 STM",
    "Artist": "Julian Bleecker",
    "Copyright": "© 2025 Julian Bleecker"
}

# Convert EXIF metadata to a JSON string
exif_json = json.dumps(exif_metadata, indent=2)

# Generate QR code from EXIF JSON string
img = create_qr_code(exif_json, box_size=10, border=4)
img.save("exif_qr_demo.png")
print("Demo QR code with EXIF metadata saved as exif_qr_demo.png")
