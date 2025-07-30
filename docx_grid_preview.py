import os
from pathlib import Path
from docx import Document
import logging

def extract_docx_text(docx_path):
    try:
        doc = Document(docx_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n'.join(paragraphs)
    except Exception as e:
        logging.error(f"Error reading {docx_path}: {e}")
        return ""

def process_docx_file(docx_path):
    txt_path = docx_path.with_suffix('.txt')
    text = extract_docx_text(docx_path)
    if not text:
        logging.info(f"No text found in {docx_path}")
        return
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    logging.info(f"Saved text: {txt_path}")

def find_docx_files(root_dir):
    return list(Path(root_dir).rglob('*.docx'))

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract text from DOCX files and save as .txt.')
    parser.add_argument('--root-dir', required=True, help='Root directory to search for DOCX files')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    docx_files = find_docx_files(args.root_dir)
    logging.info(f"Found {len(docx_files)} DOCX files.")
    for docx_path in docx_files:
        logging.info(f"Processing {docx_path}")
        process_docx_file(docx_path)

if __name__ == "__main__":
    main()
