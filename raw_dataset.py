"""Download and extract an original ZIP without changing its source tables."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parent


def index_raw_directory(directory):
    """Record all ZIPs in a local snapshot without copying or extracting them."""
    directory = Path(directory).expanduser().resolve()
    archives = sorted(directory.glob('*.zip'))
    if not archives:
        raise ValueError(f'No ZIP archives found in {directory}')
    records = []
    for archive in archives:
        print(f'Indexing {archive.name}...', flush=True)
        checksum = hashlib.sha256()
        with archive.open('rb') as source:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                checksum.update(block)
        with zipfile.ZipFile(archive) as zipped:
            members = [{'name': m.filename, 'bytes': m.file_size}
                       for m in zipped.infolist() if not m.is_dir()]
        records.append({'name': archive.name, 'bytes': archive.stat().st_size,
                        'sha256': checksum.hexdigest(), 'members': members})
    manifest = {'scope': 'All ZIP files in the supplied directory; PDFs excluded. '
                         'Inventory only; source completeness and row contents not validated.',
                'archives': records}
    (ROOT / 'raw_dataset_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Absolute machine-specific paths stay in the Git-ignored data directory.
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/raw_location.json').write_text(json.dumps({'directory': str(directory)}, indent=2) + '\n')
    print(f'Indexed {len(records)} archives; originals remain in {directory}')
    return manifest


def import_raw_zip(*, url=None, local_zip=None, expected_sha256=None, data_dir=None):
    if bool(url) == bool(local_zip):
        raise ValueError('Supply exactly one download URL or local ZIP')
    if url and urlsplit(url).scheme != 'https':
        raise ValueError('Use an HTTPS direct download URL')
    data_dir = Path(data_dir) if data_dir is not None else ROOT / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    destination = data_dir / 'raw'
    if destination.exists():
        raise FileExistsError(f'{destination} already exists; move it aside before importing a new snapshot')
    with tempfile.TemporaryDirectory(dir=data_dir) as temp:
        staging = Path(temp)
        archive = staging / 'source.zip'
        if url:
            print('Downloading raw ZIP...', flush=True)
            with urlopen(url, timeout=60) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
        else:
            shutil.copyfile(Path(local_zip).expanduser(), archive)
        checksum = hashlib.sha256()
        with archive.open('rb') as source:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                checksum.update(block)
        actual = checksum.hexdigest()
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError('ZIP SHA-256 does not match the expected dataset')
        extracted = staging / 'files'
        extracted.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            # Validate all destinations before writing any archive contents.
            for member in zipped.infolist():
                target = (extracted / member.filename).resolve()
                if not target.is_relative_to(extracted.resolve()) or '\\' in member.filename:
                    raise ValueError(f'Unsafe ZIP entry: {member.filename}')
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f'ZIP symlinks are unsupported: {member.filename}')
            zipped.extractall(extracted)
        bundle = staging / 'bundle'
        bundle.mkdir()
        archive.rename(bundle / 'source.zip')
        extracted.rename(bundle / 'files')
        (bundle / 'manifest.json').write_text(json.dumps({
            'archive': 'source.zip', 'sha256': actual,
            'source_name': Path(local_zip).name if local_zip else 'shared HTTPS download',
            'scope': 'Original ZIP and extracted files; no cleaning or Parquet conversion performed.',
        }, indent=2) + '\n')
        bundle.rename(destination)
    print(f'Raw dataset saved to {destination}\nSHA-256: {actual}')
    return destination
