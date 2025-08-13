// batch_create_file_cards.js
// Usage: node batch_create_file_cards.js --page-size LARGE_TAROT --root-dir ../SlackExporterForOmata

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = require('minimist')(process.argv.slice(2));
const pageSize = args['page-size'] || 'LARGE_TAROT';
const rootDir = args['root-dir'] || '../SlackExporterForOmata';
const outputDir = args['output-dir'] || 'cards_output';

if (!fs.existsSync(rootDir)) {
  console.error(`Root directory not found: ${rootDir}`);
  process.exit(1);
}

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const channelDirs = fs.readdirSync(rootDir).filter(dir => {
  const fullPath = path.join(rootDir, dir);
  return fs.statSync(fullPath).isDirectory() && fs.existsSync(path.join(fullPath, 'files'));
});

channelDirs.forEach(channel => {
  const inputDir = path.join(rootDir, channel, 'files');
  const channelOutputDir = path.join(outputDir, `${channel}_file_cards_output`);
  console.log(`Processing channel: ${channel}`);
  const cmd = `python3 create_file_cards.py --page-size "${pageSize}" --input-dir "${inputDir}" --output-dir "${channelOutputDir}" --cmyk-mode --max-depth 2 --border-color "250,250,174" --delete-cards-after-pdf`;
  try {
    execSync(cmd, { stdio: 'inherit' });
  } catch (err) {
    console.error(`Error processing channel ${channel}:`, err.message);
  }
});

console.log('Batch card creation complete.');
