# Module 6 Reproducibility Check

檢查時間：2026-10-03T22:19:11Z 至 2026-10-04T00:47:03Z（UTC）。

## 閱讀與環境

已閱讀：

- `README.md`
- `docs/CLEANING.md`
- `scripts/clean_communitynotes.py`
- `scripts/validate_communitynotes.py`

文件指定完整流程為建立 `.venv`、安裝 `requirements-cleaning.txt`、跑單元測試，再從原始 ZIP 執行 `scripts/clean_communitynotes.py`。清理程式會串流讀取 ZIP，不解壓或修改原始資料；輸出目錄需與 raw tree 分離，且在 repo 內必須受 Git ignore 保護。流程在 checkpoint 發現可用空間低於 3 GiB 時會停止。

實際依賴版本：

- Python 3.13.2
- duckdb 1.5.6
- pyarrow 25.0.1
- pytz 2026.4

`.venv` 沒有 `pip` module，因此未用 `pip freeze`；以上版本由實際 import 取得。

## 磁碟與執行

重跑前可用空間約 23 GiB；既有驗證輸出 `data/cleaning_run` 約 12 GiB，原始 ZIP 目錄約 12 GiB。空間偏緊，但足以嘗試；使用 `--workers 1` 降低同時 scratch/partial 空間壓力。重跑後可用空間約 14 GiB。

新輸出資料夾：

- `data/repro_cleaning_run`

確認 `data/repro_cleaning_run/cleaned/probe.parquet` 受 `.gitignore` 的 `data/` 規則排除。未覆蓋 `data/cleaning_run`，未修改原始 ZIP。

實際重跑命令：

```sh
.venv/bin/python scripts/clean_communitynotes.py \
  --raw-dir /Users/bobo/dso576/project/raw/communitynotes/data \
  --output-dir data/repro_cleaning_run \
  --workers 1
```

新 run 結果：

- `reports/05_validation.json`: `status=passed`
- scope: full dataset
- source files: 17
- output bytes: 12,409,890,919
- all input rows retained: true
- joins preserve analysis row counts: true
- rating aggregation reconciles: true

單元測試：

```sh
.venv/bin/python -m unittest discover -s tests -v
```

結果：11 tests passed。

## 比較方法

詳細機器可讀結果：`data/module6_validation/reproducibility_comparison.json`。

比較範圍：

- 新舊輸出的相對檔案清單。
- 所有 Parquet 檔的 schema/type、row count、內容指紋。
- JSON reports 的 raw SHA-256、去除 run metadata/path 後的結構比較、以及排序 canonical 後的比較。
- `catalog.sql` 與 Markdown report 的 raw SHA-256 與 run path normalized 文字比較。

Parquet 內容比較逐檔進行，未載入整套資料到 Python 記憶體。每個檔案用 DuckDB 讀取並計算：

- `DESCRIBE SELECT * FROM read_parquet(...)`
- `count(*)`
- order-insensitive row hash fingerprints: `bit_xor(hash(* COLUMNS(*)))` 與 `sum(CAST(hash(* COLUMNS(*)) AS HUGEINT))`
- order-sensitive fingerprints: 對 `row_number() OVER ()` 加入 hash，以偵測列順序差異

此方法不是只看 row count；大型 ratings 分區、join flags 與 summary 均逐檔掃描比較內容指紋。

## 結果

檔案清單：

- old files: 86
- new files: 86
- missing in new: none
- extra in new: none

Parquet：

- files compared: 35
- schema/type mismatches: none
- row count mismatches: none
- order-insensitive content fingerprint mismatches: none
- order-sensitive fingerprint differences:
  - `audit/noteStatusHistory-join-flags.parquet`
  - `audit/notes-join-flags.parquet`
  - `audit/ratings-join-flags.parquet`
  - `summaries/ratings_by_note.parquet`

判定：上述 4 個 Parquet 檔內容集合一致，但列順序不同。這些檔案由 SQL join/aggregation 產生，查詢未指定最終 `ORDER BY`，因此列順序差異屬執行順序/輸出順序差異，不是資料內容差異。

JSON reports：

- raw SHA-256 有差異的 JSON 主要包含 `manifest.json`、`reports/rules.json`、`reports/05_validation.json`、部分 profile/transform/duplicate reports。
- 去除 `run_time`、`inspection_time_utc`、`output_bytes` 與 run-specific path 後，仍有差異者集中在 transform reports 的 `value_mappings` list 順序。
- 將 list-of-dicts 依內容 canonical sort 後，JSON reports 無資料差異。

文字檔：

- `catalog.sql` raw SHA-256 不同，原因是其中嵌入了不同輸出資料夾的絕對路徑。
- 將 run path normalize 後，`catalog.sql` 無差異。

## 結論

Module 6 可重現性檢查通過。從相同原始 ZIP 在獨立資料夾完整重跑後，新舊結果的檔案清單、Parquet 欄位與型態、列數及資料內容一致。觀察到的差異限於：

- 新舊 run 的執行時間、輸出路徑、輸出 bytes 等中繼資訊。
- 未指定排序的 join/summary Parquet 檔列順序。
- JSON report 中 `value_mappings` 等 list 的輸出順序。

未發現資料內容差異。所有完整資料仍在 Git-ignored `data/` 目錄下；未 Commit、未 Push。
