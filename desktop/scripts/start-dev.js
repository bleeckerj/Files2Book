import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import getPort from 'get-port';

const PORT_CANDIDATES = [3000, 3001, 3002, 3003, 4000];

async function main() {
  const port = await getPort({ port: PORT_CANDIDATES });
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const projectRoot = path.resolve(scriptDir, '..');
  const srcTauriDir = path.join(projectRoot, 'src-tauri');
  const baseConfigPath = path.join(srcTauriDir, 'tauri.conf.json');
  const devConfigPath = path.join(srcTauriDir, 'tauri.dev.conf.json');

  const baseConfig = JSON.parse(fs.readFileSync(baseConfigPath, 'utf8'));
  const devConfig = {
    ...baseConfig,
    build: {
      ...baseConfig.build,
      devPath: `http://localhost:${port}`,
      beforeDevCommand: '',
    },
  };

  fs.writeFileSync(devConfigPath, JSON.stringify(devConfig, null, 2));

  const env = { ...process.env, PORT: String(port) };
  const vite = spawn('npm', ['run', 'dev', '--', '--port', String(port)], {
    cwd: projectRoot,
    env,
    stdio: 'inherit',
  });

  const tauri = spawn(
    'npx',
    ['tauri', 'dev', '-c', devConfigPath, '--no-dev-server'],
    {
      cwd: projectRoot,
      env,
      stdio: 'inherit',
    }
  );

  const cleanup = () => {
    if (vite && !vite.killed) {
      vite.kill();
    }
    if (tauri && !tauri.killed) {
      tauri.kill();
    }
    if (fs.existsSync(devConfigPath)) {
      fs.rmSync(devConfigPath);
    }
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('exit', cleanup);
}

main().catch((error) => {
  console.error('Failed to start dev environment', error);
  process.exit(1);
});
