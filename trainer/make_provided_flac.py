"""Provided DIs for the browser trainer as 16-bit FLAC. Each 32 s float32 DI (browser_teacher_069/data/di*.f32) is quantised to int16 against its
own peak (q = round(x/step), |q| <= 32000) and written losslessly. The page decodes q/32768 and multiplies by
`scale` = 32768*step, giving the training samples (quantisation -101 dBFS of peak, 18-30 dB below each recording's
noise floor). manifest.json gains `provided_di_flac` [{file, name, samples, scale, sha256 (FLAC bytes),
decoded_sha256 (float32 LE samples after scaling)}]; the page refuses any file or decode that does not match."""
import hashlib, io, json
from pathlib import Path
import numpy as np, soundfile as sf
BASE = 'https://lttc-data.sfranjou.workers.dev/trainer/v1/'   # data Worker (tools/tone_trainer/data_worker) in front of R2 bucket lttc-data; upload: npx wrangler r2 object put lttc-data/trainer/v1/<file> --remote
D = Path(__file__).resolve().parents[2] / 'work/tone_capture/browser_teacher_069/data'
m = json.loads((D / 'manifest.json').read_text()); rows = []
for k, src in enumerate(m['provided_di']):
    x = np.fromfile(D / src['file'], dtype='<f4').astype(np.float64)
    step = float(np.abs(x).max()) / 32000; q = np.round(x / step).astype(np.int16)
    buf = io.BytesIO(); sf.write(buf, q, 44100, format='FLAC', subtype='PCM_16'); raw = buf.getvalue()
    back, rate = sf.read(io.BytesIO(raw), dtype='int16'); assert rate == 44100 and np.array_equal(back, q)
    scale = 32768 * step; decoded = ((q.astype(np.float64) / 32768) * scale).astype('<f4')
    name = f'di{k}.flac'; (D / name).write_bytes(raw)
    rows.append(dict(file=name, name=src['name'], samples=int(len(q)), scale=scale, sha256=hashlib.sha256(raw).hexdigest(),
                     decoded_sha256=hashlib.sha256(decoded.tobytes()).hexdigest(),
                     error_dbfs_of_peak=float(20 * np.log10(np.sqrt(np.mean((decoded - x) ** 2)) / np.abs(x).max()))))
m['provided_di_flac'] = rows
m['provided_di_base'] = BASE   # where the page fetches the FLACs (data Worker over R2)
(D / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
print([(r['file'], round(len((D / r['file']).read_bytes()) / 1e6, 2), round(r['error_dbfs_of_peak'], 1)) for r in rows])
