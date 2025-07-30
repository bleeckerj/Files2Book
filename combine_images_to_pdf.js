#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const PDFDocument = require('pdfkit');
const { program } = require('commander');

/**
 * Combine images from a directory into a single PDF
 * Supports CMYK or RGB color mode
 */
async function combineImagesToPdf(options) {
  const {
    inputDir,
    outputFile,
    cmykMode,
    pageSize,
    dpi,
    sortOrder,
    filter,
    quiet
  } = options;

  const log = quiet ? () => {} : console.log;
  const warn = quiet ? () => {} : console.warn;
  
  // Silence Sharp's internal logging if quiet mode is enabled
  if (quiet) {
    sharp.quiet(true); // Turn off sharp's warnings
  }

  log(`Starting PDF creation: ${outputFile} (CMYK mode: ${cmykMode ? 'YES' : 'NO'})`);
  
  // Define page dimensions
  const pageSizes = {
    'a5': { width: 5.8 * dpi, height: 8.3 * dpi },
    'a4': { width: 8.3 * dpi, height: 11.7 * dpi },
    'a3': { width: 11.7 * dpi, height: 16.5 * dpi },
    'letter': { width: 8.5 * dpi, height: 11 * dpi },
    'legal': { width: 8.5 * dpi, height: 14 * dpi },
    'tabloid': { width: 11 * dpi, height: 17 * dpi },
    // Add other page sizes as needed
  };
  
  // If custom size, parse it (format: WxH in inches)
  let pageWidth, pageHeight;
  
  if (pageSizes[pageSize.toLowerCase()]) {
    pageWidth = pageSizes[pageSize.toLowerCase()].width;
    pageHeight = pageSizes[pageSize.toLowerCase()].height;
  } else if (pageSize.toLowerCase().includes('x')) {
    const [w, h] = pageSize.split('x').map(dim => parseFloat(dim) * dpi);
    pageWidth = w;
    pageHeight = h;
  } else {
    log(`Unknown page size: ${pageSize}, defaulting to A4`);
    pageWidth = pageSizes.a4.width;
    pageHeight = pageSizes.a4.height;
  }
  
  log(`Page size: ${pageWidth/dpi}x${pageHeight/dpi} inches (${pageWidth}x${pageHeight} pixels at ${dpi} DPI)`);

  // Get all image files from the directory
  let files = await fs.promises.readdir(inputDir);
  
  // Filter by extension if specified
  const supportedExtensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.gif', '.svg', '.avif'];
  files = files.filter(file => {
    const ext = path.extname(file).toLowerCase();
    return supportedExtensions.includes(ext);
  });

  // Apply additional filter if specified
  if (filter) {
    const filterRegex = new RegExp(filter);
    files = files.filter(file => filterRegex.test(file));
  }

  // Sort files
  switch (sortOrder) {
    case 'name':
      files.sort();
      break;
    case 'name-desc':
      files.sort().reverse();
      break;
    case 'date':
      files = await Promise.all(files.map(async file => {
        const stats = await fs.promises.stat(path.join(inputDir, file));
        return { file, date: stats.mtime };
      }));
      files.sort((a, b) => a.date - b.date);
      files = files.map(item => item.file);
      break;
    case 'date-desc':
      files = await Promise.all(files.map(async file => {
        const stats = await fs.promises.stat(path.join(inputDir, file));
        return { file, date: stats.mtime };
      }));
      files.sort((a, b) => b.date - a.date);
      files = files.map(item => item.file);
      break;
    default:
      files.sort();
  }

  if (files.length === 0) {
    // Always show errors, even in quiet mode
    console.error('No compatible image files found in the directory');
    return;
  }
  
  log(`Found ${files.length} image files to process`);

  // Create a PDF document with the specified page size
  const doc = new PDFDocument({
    size: [pageWidth, pageHeight], 
    autoFirstPage: false,
    // PDFKit uses points (72 DPI), so convert our dimensions
    margin: 0
  });
  
  // Pipe the PDF to a write stream
  doc.pipe(fs.createWriteStream(outputFile));

  // Process each image
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const filePath = path.join(inputDir, file);
    
    try {
      log(`Processing ${i+1}/${files.length}: ${file}`);
      
      // Start a new page
      doc.addPage({
        size: [pageWidth, pageHeight],
        margin: 0
      });
      
      let processedImagePath;
      
      // If CMYK conversion is needed
      if (cmykMode) {
        // Create a temporary file for the CMYK version
        const tempDir = path.join(inputDir, 'temp_cmyk');
        if (!fs.existsSync(tempDir)) {
          fs.mkdirSync(tempDir, { recursive: true });
        }
        
        processedImagePath = path.join(tempDir, `cmyk_temp_${i}.jpg`);
        log(`Converting to CMYK: ${file}`);
        
        // Use sharp to convert the image to CMYK
        await sharp(filePath)
          .resize(pageWidth, pageHeight, { 
            fit: 'contain', 
            position: 'center',
            background: { r: 255, g: 255, b: 255, alpha: 1 }
          })
          .toColorspace('cmyk')
          .jpeg({ quality: 95 })
          .toFile(processedImagePath);
      } else {
        // For RGB, use the original file
        processedImagePath = filePath;
      }
      
      // Add the image to the PDF, scaling to fit the page
      doc.image(processedImagePath, 0, 0, {
        fit: [pageWidth, pageHeight],
        align: 'center',
        valign: 'center'
      });
      
      // Clean up the temporary CMYK file if it was created
      if (cmykMode && fs.existsSync(processedImagePath) && processedImagePath.includes('temp_cmyk')) {
        fs.unlinkSync(processedImagePath);
      }
      
    } catch (err) {
      // Always show errors, even in quiet mode
      console.error(`Error processing ${file}: ${err.message}`);
    }
  }
  
  // Finalize the PDF
  doc.end();
  log(`PDF creation complete: ${outputFile}`);
  
  // Clean up any temporary directories
  const tempDir = path.join(inputDir, 'temp_cmyk');
  if (fs.existsSync(tempDir)) {
    fs.rmdir(tempDir, { recursive: true }, (err) => {
      if (err) console.error(`Error cleaning up temp directory: ${err.message}`);
    });
  }
}

// Set up the command line interface
program
  .name('combine-images-to-pdf')
  .description('Combine images from a directory into a single PDF (RGB or CMYK)')
  .version('1.0.0')
  .requiredOption('-i, --input-dir <dir>', 'Directory containing the images')
  .requiredOption('-o, --output-file <file>', 'Output PDF file path')
  .option('-c, --cmyk-mode', 'Use CMYK color mode', false)
  .option('-p, --page-size <size>', 'Page size (A4, LETTER, TABLOID, WxH in inches)', 'A4')
  .option('-d, --dpi <number>', 'DPI for page size calculations', 300)
  .option('-s, --sort-order <order>', 'Sort order (name, name-desc, date, date-desc)', 'name')
  .option('-f, --filter <pattern>', 'Filter files by name pattern (regex)')
  .option('-q, --quiet', 'Suppress all non-essential output', false)
  .action((options) => {
    combineImagesToPdf(options)
      .catch(err => console.error(`Error: ${err.message}`));
  });

program.parse(process.argv);
