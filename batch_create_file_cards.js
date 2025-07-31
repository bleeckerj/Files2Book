// batch_create_file_cards.js
// Usage: node batch_create_file_cards.js --page-size LARGE_TAROT --root-dir ../SlackExporterForOmata

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = require('minimist')(process.argv.slice(2));
const pageSize = args['page-size'] || 'LARGE_TAROT';
const rootDir = args['root-dir'] || '../SlackExporterForOmata';

if (!fs.existsSync(rootDir)) {
  console.error(`Root directory not found: ${rootDir}`);
  process.exit(1);
}

const channelDirs = fs.readdirSync(rootDir).filter(dir => {
  const fullPath = path.join(rootDir, dir);
  return fs.statSync(fullPath).isDirectory() && fs.existsSync(path.join(fullPath, 'files'));
});

channelDirs.forEach(channel => {
  const inputDir = path.join(rootDir, channel, 'files');
  const outputDir = `${channel}_file_cards_output`;
  const cmd = `python3 create_file_cards.py --page-size ${pageSize} --input-dir ${inputDir} --output-dir ${outputDir} --cmyk-mode`;
  console.log(`Processing channel: ${channel}`);
  try {
    execSync(cmd, { stdio: 'inherit' });
  } catch (err) {
    console.error(`Error processing channel ${channel}:`, err.message);
  }
});

console.log('Batch card creation complete.');
