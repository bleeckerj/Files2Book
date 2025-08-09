import qrcode
from PIL import Image

def create_qr_code(data: str, box_size: int = 10, border: int = 4) -> Image.Image:
    """
    Generate a QR code image from a string.
    Args:
        data (str): The string to encode in the QR code.
        box_size (int): Size of each QR box in pixels.
        border (int): Border size in boxes.
    Returns:
        PIL.Image.Image: The generated QR code image.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.convert("RGBA")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a QR code image from a string.")
    parser.add_argument("--data", required=True, help="String to encode in the QR code.")
    parser.add_argument("--output", required=True, help="Output image file path.")
    parser.add_argument("--box-size", type=int, default=10, help="Size of each QR box in pixels.")
    parser.add_argument("--border", type=int, default=4, help="Border size in boxes.")
    args = parser.parse_args()

    img = create_qr_code(args.data, box_size=args.box_size, border=args.border)
    img.save(args.output)
    print(f"QR code saved to {args.output}")
