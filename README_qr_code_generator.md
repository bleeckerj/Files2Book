# QR Code Generator

This module provides a simple way to generate QR code images from strings, either programmatically or via the command line.

## Usage as a Python Module

Import the function and generate a QR code:

```python
from qr_code_generator import create_qr_code
img = create_qr_code("Hello World")
img.save("qr.png")
```

## Command Line Usage

You can also run the script directly from the command line:

```sh
python qr_code_generator.py --data "Hello World" --output qr.png --box-size 10 --border 4
```

- `--data` (required): The string to encode in the QR code.
- `--output` (required): Output image file path (e.g., qr.png).
- `--box-size`: Size of each QR box in pixels (default: 10).
- `--border`: Border size in boxes (default: 4).

## Requirements

- `qrcode` (install with `pip install qrcode[pil]`)
- `Pillow` (install with `pip install Pillow`)

## Example

Generate a QR code for a URL:

```sh
python qr_code_generator.py --data "https://example.com" --output example_qr.png
```

## License

MIT License
