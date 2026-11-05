# Raw dataset sharing and import

### Share the full raw dataset

The current local snapshot contains 17 ZIP archives (about 12 GB). To inventory
an existing folder without duplicating or extracting its contents, run:

```bash
python3 prepare_dashboard.py --raw-dir '/path/to/communitynotes/data'
```

This records filenames, archive sizes, SHA-256 checksums, and enclosed filenames
in `raw_dataset_manifest.json`. It excludes the course PDFs. The local folder
path is saved separately in Git-ignored `data/raw_location.json`. Indexing reads
every archive to calculate checksums; it does not validate every data row.
The original ZIPs stay where they are. This raw-data command needs only Python's
standard library.

**Team access still requires sharing the actual ZIPs.** A local path on one
computer is not a shared download location. Upload all ZIPs to team-accessible
storage, then share that location and this manifest. Each teammate can inventory
their downloaded folder and compare checksums. The URL command below imports
one ZIP at a time; it does not download this entire multi-archive snapshot.

Keep the original ZIP in team-accessible storage and share a direct HTTPS download
link. Do not paste its contents into Python or commit the large archive to Git.
Teammates can download and extract the exact same ZIP with:

```bash
python prepare_dashboard.py --raw-url 'https://YOUR-STORAGE/YOUR-DATASET.zip'
```

Replace the example URL with your actual direct download link (an HTML preview or
sign-in page will not work). Do not commit private links containing access tokens.
If you already downloaded the ZIP, use:

```bash
python prepare_dashboard.py --raw-zip '/path/to/dataset.zip'
```

Both commands preserve the ZIP at `data/raw/source.zip`, extract all its files
under `data/raw/files/`, and record a SHA-256 in `data/raw/manifest.json`.
The whole `data/` directory is ignored by Git. Share the printed checksum with
teammates; add `--sha256 CHECKSUM` to either command to verify their download.
Existing `data/raw/` is never overwritten; move it aside to import another snapshot.
Allow disk space for both the ZIP and its complete extracted contents.

Importing a ZIP only installs raw data. It does not run the separate team cleaning
workflows or convert arbitrary raw tables to dashboard Parquet. Running
`python prepare_dashboard.py` without options retains the existing cleaned-input
audit and Parquet build described below. The bundled Parquet files are compact
dashboard inputs, not a copy of the full raw dataset.

