"""Generate/check additive assistance v1 IR, corpus and TS/Rust renderings.

The existing declaration v1 and CONTRACT_VERSION pins are not changed. This
module is uncommitted development output until its own release pin is assigned.
"""
from pathlib import Path
import sys, tempfile, subprocess, hashlib, json
if not sys.flags.utf8_mode:
    raise SystemExit(subprocess.call([sys.executable, '-X', 'utf8', __file__, *sys.argv[1:]]))
ROOT = Path(__file__).resolve().parents[1]
TAUT_PIN = '3c6d07ecb4cdb2496dd1a7524e270f8cc11a7640'
actual_taut = subprocess.check_output(['git', '-C', str(ROOT.parent / 'taut'), 'rev-parse', 'HEAD'], text=True).strip()
if actual_taut != TAUT_PIN:
    raise SystemExit('Taut differs from the assistance generator pin; review before regeneration.')
sys.path.insert(0, str(ROOT.parent / 'taut/src'))
from taut.ir.load import load_schema
from taut.ir.validate import validate_or_raise
from taut.ir.export import export_to
from taut.gen.scaffold import emit
from taut.corpus import kit, synth

schema = load_schema(ROOT / 'ir/assistance.taut.py')
validate_or_raise(schema)
corpus = kit.build_corpus(schema, dict(synth.synth_values(schema)))
ts_roots = [ROOT.parent / 'glade-decl-ts/src/assistance', ROOT.parents[1] / 'chopstitch-wz/glade-decl-ts/src/assistance']
rs_root = ROOT.parent / 'glade-decl-rs/src/assistance'
with tempfile.TemporaryDirectory(prefix='assistance-taut-') as folder:
    out = Path(folder)
    export_to(schema, out / 'assistance.ir.json')
    emit(schema, out, langs=['typescript', 'rust'], services=[], runtime=True)
    artifacts = [(ROOT / 'ir/assistance.ir.json', (out / 'assistance.ir.json').read_bytes()),
                 (ROOT / 'corpus/assistance.v1.json', kit.golden_json(corpus).encode())]
    provenance = (json.dumps({'moduleVersion': 1, 'status': 'development-uncommitted-not-release-pinned',
        'tautCommit': TAUT_PIN, 'schemaSha256': hashlib.sha256((ROOT / 'ir/assistance.taut.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()}, indent=2) + '\n').encode()
    artifacts.append((ROOT / 'corpus/assistance.provenance.json', provenance))
    for dest in ts_roots:
        artifacts.append((dest / 'ir.ts', b'// GENERATED from assistance.taut.py; do not edit.\nexport default ' + (out / 'assistance.ir.json').read_bytes() + b';\n'))
        for source in (out / 'typescript').glob('*.ts'):
            artifacts.append((dest / source.name, source.read_bytes()))
        artifacts.extend([(dest / 'assistance.ir.json', (out / 'assistance.ir.json').read_bytes()),
                          (dest / 'assistance.v1.json', kit.golden_json(corpus).encode()),
                          (dest / 'assistance.provenance.json', provenance)])
    for source in (out / 'rust').glob('*.rs'):
        # Namespace the generated module and its matching runtime together. The
        # older declaration module's runtime lacks try_decode_with; keep it intact.
        if source.name in ('api.rs', 'cbor.rs'):
            generated = source.read_bytes().replace(b'crate::cbor', b'crate::assistance::cbor')
            formatted = subprocess.run(['rustup', 'run', '1.95.0', 'rustfmt', '--edition', '2021'], input=generated, capture_output=True, check=True).stdout
            artifacts.append((rs_root / source.name, formatted))
    vectors = kit.rust_vectors(schema, corpus).replace('crate::', 'crate::assistance::')
    formatted = subprocess.run(['rustup', 'run', '1.95.0', 'rustfmt', '--edition', '2021'], input=vectors.encode(), capture_output=True, check=True).stdout
    artifacts.append((rs_root / 'vectors.rs', formatted))
    artifacts.append((rs_root / 'assistance.provenance.json', provenance))
    for destination, data in artifacts:
        data = data.replace(b'\r\n', b'\n')
        if '--check' in sys.argv:
            if not destination.exists() or destination.read_bytes() != data:
                raise SystemExit('Generated assistance artifact differs: ' + str(destination))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Replace rather than write through pnpm hardlinks.
            temporary = destination.with_suffix(destination.suffix + '.tmp')
            temporary.write_bytes(data)
            temporary.replace(destination)
print('Assistance module artifacts match.' if '--check' in sys.argv else 'Generated assistance module artifacts.')

