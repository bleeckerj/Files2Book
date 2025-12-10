import { type DragEvent, useCallback, useMemo, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

type File2BookOptions = {
  page_size: string;
  aspect_ratio: string;
  depth?: number;
};

type Status = 'idle' | 'running' | 'done' | 'error';


const PAGE_SIZE_OPTIONS = [
  { label: 'A5', value: 'A5', dims: [5.83, 8.27] },
  { label: 'A4', value: 'A4', dims: [8.27, 11.69] },
  { label: 'Digest', value: 'DIGEST', dims: [5.5, 8.5] },
  { label: 'Digest Full Bleed', value: 'DIGEST_FULLBLEED', dims: [5.75, 8.75] },
  { label: 'Letter', value: 'LETTER', dims: [8.5, 11] },
  { label: 'PocketBook', value: 'POCKETBOOK', dims: [4.25, 6.87] },
  { label: 'PocketBook Full Bleed', value: 'POCKETBOOK_FULLBLEED', dims: [4.5, 7.12] },
  { label: 'Trade Large', value: 'TRADE_LARGE', dims: [7, 9] },
  { label: 'Poker', value: 'POKER', dims: [2.48, 3.46] },
  { label: 'Bridge', value: 'BRIDGE', dims: [2.24, 3.46] },
  { label: 'Mini', value: 'MINI', dims: [1.73, 2.68] },
  { label: 'Large Tarot', value: 'LARGE_TAROT', dims: [2.76, 4.72] },
  { label: 'Small Tarot', value: 'SMALL_TAROT', dims: [2.76, 4.25] },
  { label: 'Large Square', value: 'LARGE_SQUARE', dims: [2.76, 2.76] },
  { label: 'Small Square', value: 'SMALL_SQUARE', dims: [2.48, 2.48] },
];
const DEFAULT_ASPECT_RATIO = '3:2';

type PageSizeButtonGridProps = {
  options: readonly { label: string; value: string }[];
  value: string;
  onChange: (value: string) => void;
};

const MAX_DISPLAY_DIMENSION = 140;

const PageSizeButtonGrid = ({ options, value, onChange }: PageSizeButtonGridProps) => {
  const scale = Math.max(
    ...options.map((entry) => Math.max(entry.dims[0], entry.dims[1]))
  );
  return (
    <div className="page-size-grid">
      {options.map((option) => {
        const [w, h] = option.dims;
        const ratio = MAX_DISPLAY_DIMENSION / scale;
        const displayWidth = Math.round(w * ratio * 10) / 10;
        const displayHeight = Math.round(h * ratio * 10) / 10;
        return (
        <button
          key={option.value}
          type="button"
          className={`page-size-pill ${value === option.value ? 'selected' : ''}`}
          style={{ width: `${displayWidth}px`, height: `${displayHeight}px` }}
          onClick={() => onChange(option.value)}
          title={`${option.label} — ${option.dims[0]}″×${option.dims[1]}″`}
        >
          <span className="sr-only">{option.label}</span>
        </button>
        );
      })}
    </div>
  );
};

const App = () => {
  const [inputPath, setInputPath] = useState('');
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0].value);
  const [depth, setDepth] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const statusLabel = useMemo(() => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'done':
        return 'Done';
      case 'error':
        return 'Error';
      default:
        return 'Idle';
    }
  }, [status]);

  const options: File2BookOptions = useMemo(
    () => ({
      page_size: pageSize,
      aspect_ratio: DEFAULT_ASPECT_RATIO,
      depth: depth ? Number(depth) : undefined,
    }),
    [pageSize, depth]
  );

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setInputPath(file.path);
      setMessage(null);
    }
  }, []);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  }, []);

  const runFile2Book = useCallback(async () => {
    if (!inputPath) {
      setMessage('Please drop a file or folder.');
      return;
    }

    setStatus('running');
    setProgress(null);
    setMessage(null);

    try {
      const finalPath = await invoke<string>('run_file2book', {
        input_path: inputPath,
        options,
      });
      setStatus('done');
      setProgress(1);
      setMessage(`Created book at ${finalPath}`);
    } catch (error) {
      setStatus('error');
      setMessage(typeof error === 'string' ? error : 'An unexpected error occurred');
    }
  }, [inputPath, options]);

  return (
    <div className="neo-screen">
      <div className="neo-shell">
        <section className="neo-panel">
          <div className="flex items-center justify-between">
            {/* <p className="text-[0.65rem] uppercase tracking-[0.4em] text-[var(--color-muted)]">drop zone</p> */}
            <div />
            <span className="neo-status">{statusLabel}</span>
          </div>

          <div className="neo-dropzone" onDrop={handleDrop} onDragOver={handleDragOver}>
            <p className="neo-drop-title">Drop any folder or file</p>
            <p className="neo-drop-path">{inputPath || 'Waiting for input…'}</p>
          </div>

          <div className="neo-detail-panel">
            <p>Status</p>
            <p className="text-[var(--color-text)] text-[0.75rem] font-normal normal-case">
              {message ?? 'Idle, waiting for your command.'}
            </p>
            {progress !== null && (
              <div className="neo-progress">
                <div className="neo-progress-fill" style={{ width: `${Math.min(progress * 100, 100)}%` }} />
              </div>
            )}
          </div>

            <PageSizeButtonGrid options={PAGE_SIZE_OPTIONS} value={pageSize} onChange={setPageSize} />

          <button
            className="neo-button"
            type="button"
            onClick={runFile2Book}
            disabled={status === 'running'}
          >
            Run File2Book
          </button>
        </section>
      </div>
    </div>
  );
};

export default App;
