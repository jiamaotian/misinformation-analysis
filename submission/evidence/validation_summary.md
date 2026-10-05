# Module 6 完整資料驗證

提交副本補充：此檔從 `data/module6_validation/validation_report.md` 複製而來，原文記錄的是五筆人工核對完成前的驗證狀態。五筆人工核對後續已完成，提交版證據見 `submission/evidence/manual_cases.md`。本檔其餘全量驗證結果仍作為完整資料驗證摘要。

驗證完成時間（UTC）：2026-10-03T21:53:20.375418+00:00。

本次只新增本機驗證證據，未修改清理規則、程式或既有清理輸出；未 Commit、Push 或上傳。所有證據在 Git 忽略的 `data/module6_validation/`。原始 ZIP 留在原位置。

檢查涵蓋目前計畫的五表全部 17 個 ZIP、98 個原始欄位。尚未選定專題分析 cohort、feed 或截止日，因此這是全來源清理驗證，並非最終專題指標驗證。

## 驗證方法與限制

重新讀取完整 ZIP 並核對清理前 SHA-256；將清理輸出依來源順序還原成原始 TSV 本文，對所有資料列及所有欄位做完整本文 SHA-256 比對。沒有抽樣或落地解壓縮原始資料。這補上原程式只驗證每批首尾列的限制。

另外重新掃描完整 Parquet，核對缺失數、既定映射、UTC、候選鍵、跨分檔重複、關聯基數及逐 Note 評分彙總。SQL 轉換預期取自既有 rules.json，因此可證明輸出符合該合約；不能獨立證明來源文件對模糊值的語意。計畫與程式另做人工對照，未知語意仍保留待確認。

## 驗證清單

| 檢查項目 | 預期 | 實際 | 通過／未通過 | 證據位置 |
|---|---|---|---|---|
| 範圍 | 17 個 ZIP、五表、完整列數，無樣本上限 | 17 個檔案；243,997,521 列 | 通過 | *-roundtrip.json；../cleaning_run/manifest.json |
| 原始資料完整性 | 所有 ZIP 的 SHA-256 與清理前 manifest 相同 | 17/17 相同 | 通過 | *-roundtrip.json / raw_sha256 |
| 全量原始值可還原 | 完整 TSV 本文逐位元組雜湊相同；來源列序正確 | 17/17 相同；來源錯誤 0 | 通過 | *-roundtrip.json / 兩個 tsv_body_sha256 |
| 列數與刪列 | 清理及 analysis view 保留所有非完全重複來源列 | 五表列數不變；去重排除 0 | 通過 | 下方列數表；*-keys.json |
| 候選鍵與完全重複 | 全表及跨分檔檢查，不任意保留衝突列 | 缺失候選鍵 0；重複鍵群 0；完全重複列 0 | 通過 | *-keys.json |
| 逐欄缺失值 | 原始空字串數與全量 profile 一致；輸出 null 數與清理報告一致 | 98 欄均逐欄比較 | 通過 | column_comparison.md；*-columns.json |
| 型態與類別映射 | 全部原始欄位符合既定 SQL 規則，不猜測類別 | 不符規則儲存格 0 | 通過 | *-columns.json / mapping_mismatch；../cleaning_run/reports/rules.json |
| 主要轉換報告 | 各表列數、變更列／格數與逐欄變更計數相符 | 從完整輸出的 _changed_mask 重算，與原始 transformation reports 比較 | 通過 | stage_counts.json；../cleaning_run/reports/transform/*.json |
| 時間單位與 sentinel | 毫秒轉 UTC；有符號 PCRH 與特殊值依欄位處理；minute 不轉 UTC | UTC 轉換不符 0；minute 型態 BIGINT | 通過 | *-columns.json / utc_mismatch；companions.json |
| 資格與狀態衍生欄 | 符合既定 feed、PCRH、earn-out 規則 | 各狀態衍生欄不符 0 | 通過 | companions.json |
| 文字、連結、巢狀 JSON | 原文保留；trim、連結列表、巢狀 ID 按規則衍生 | 487,851 個 request / 387,602 個 suggestion 全部檢查 | 通過 | nested.json；*-columns.json；全量還原雜湊 |
| 可疑值旗標 | 對完整資料重算既定條件；旗標計數相符 | SQL 規則計數相符；異常保留待判讀 | 通過 | *-flags.json；nested.json；原記錄級旗標 ../cleaning_run/audit/*-flags.parquet |
| 合併列數與基數 | many-to-one 或先去重成一列的 lookup；保留未匹配列 | 七個關聯的輸入／輸出列數皆相同 | 通過 | joins.json；下方關聯表；*-keys.json |
| 既有合併旗標檔 | 實際 Parquet 的列數及各旗標分布與原報告相同 | 四個完整旗標檔均一致 | 通過 | saved_join_flags.json；../cleaning_run/reports/04_cross_table.json |
| 匹配後一致性 | 僅對成功匹配者核對作者、建立時間、評分先後 | 匹配 Note/Status 的作者、時間不一致 0；匹配評分早於 Note 0 | 通過 | joins.json（未匹配者不在此檢查分母） |
| 評分彙總 | 每個 note 群組與七個計數及首末時間都重算吻合 | 3,215,297 組；不符 0 | 通過 | summary_per_note.json；metrics.json |
| 重要類別總數前後比較 | 版本、評分層級、Notes 分類、整體 Status 的有效類別計數不變 | 四組完整分布的原始／清理計數一致 | 通過 | category_totals.json；metrics.json |
| 本機保留與程式完整性 | 資料未追蹤；驗證資料夾被忽略；清理程式未改動 | Git data 追蹤檔 0；清理程式 SHA-256 與原驗證相同 | 通過 | integrity.json；.gitignore |
| 五筆人工核對 | 使用者先寫預期與理由，再揭露實際輸出 | 原始紀錄與規則已備妥；尚未比對答案 | 待完成 | manual_cases.md |
| 可疑值的真實語意 | 有來源證據才修正 | NMR -1 語意、疑似單位問題、earn-out 矛盾等仍未解決 | 無法確認 | 下方限制；*-flags.json |
| 專題 Coverage／Response Time | 確定 feed、時間窗、cutoff、有效事件與分母 | 尚未選定；不將原始 join match 比率當作最終 coverage | 待完成 | plan.md §4；metrics.json |

## 列數變化

| 資料表 | 原始列數 | 清理列數 | 差額 | 刪列原因／處理 |
|---|---|---|---|---|
| batSignals | 487,851 | 487,851 | 0 | 0；逐列保留，無結構異常或去重排除 |
| notes | 3,137,735 | 3,137,735 | 0 | 0；逐列保留，無結構異常或去重排除 |
| ratings | 235,530,477 | 235,530,477 | 0 | 0；逐列保留，無結構異常或去重排除 |
| noteStatusHistory | 3,343,818 | 3,343,818 | 0 | 0；逐列保留，無結構異常或去重排除 |
| userEnrollment | 1,497,640 | 1,497,640 | 0 | 0；逐列保留，無結構異常或去重排除 |

評分彙總另將 235,530,477 筆 rating 依 noteId 聚合成 3,215,297 列，減少 232,315,180 列是粒度改為「每個 Note 一列」的結果，並非刪除評分。sum(rating_count) 仍為 235,530,477；每組的七項計數與首末時間均逐組重算。

完全重複列為 0 的證據：所有候選鍵非空且唯一，任何完全相同原始列必然也會重複該候選鍵。Ratings 使用 `(noteId, raterParticipantId)`，不是單獨 noteId。 Ratings 的 235,530,477 列包含 3,215,297 個 noteId；超出每 ID 第一列的 232,315,180 列是正常多筆評分。

## 缺失值、型態與分母

98 個欄位完整比較見 [column_comparison.md](column_comparison.md)。原始 TSV 沒有資料庫 NULL，以精確空字串計數；清理後分別列 NULL 與空字串，避免把空白轉成 NULL 誤判為新增缺失。另列 trim 後空白及 UTC 缺失。`0`、`1`、`-1`、`[]` 不做全域缺失替換。

- 評分層級的有效分母為 **235,496,083**；缺失 34,394 筆仍保留，不能當作 NOT_HELPFUL，也不能用 legacy helpful 欄補值。Helpful 分子 144,595,094，除以有效層級為 **61.4002%**；若錯用全部 235,530,477 筆，會變成 61.3912%。這是已紀錄評分的分布，不代表一般使用者共識。
- 原始值完整還原、逐欄映射相符，因此合法類別的計數保持不變；類別大小寫未改寫，缺失未補值，新舊評分格式分開。
- 布林與整數的非空轉 NULL 以及時間字串解析失敗，均見逐欄報表。無效時間數值與語法失敗不同：數值仍可能保留，而 UTC companion 為 NULL。不得把缺失事件時間當成零秒。
- 五表所有 boolean／integer／timestamp 基底欄位的非空值轉 NULL（型態解析失敗）共 **0**。Enrollment 的無效時間數值另有 1 筆被標記；可解析成整數不代表時間合理。
- ID 的已知 `-1` sentinel 另行處理：Notes.tweetId 新增 8 個 NULL、Ratings.ratedOnTweetId 新增 2,631,448 個 NULL、Ratings.suggestionId 新增 235,514,406 個 NULL，皆可還原為原始值。這些欄位的不可用鍵不參與相應關聯，但不刪除原列，也不影響仍有效的 noteId 關聯。
- Notes 的 summary_trimmed 有 389,160 列去除外圍空白，原 summary 全數保留；其中 2 列 trim 後為空。Ratings 的 suggestion_trimmed 有 7,958 列改變，原 suggestion 保留；空白結果為 235,503,191 列（原始空字串 235,503,178，加上 13 筆僅有空白的文字）。這些都沒有造成刪列。
- Status 共 3,343,818 列，有 576,161 列記錄首個 non-NMR 時間，缺失 2,767,657 列。當前 resolved 的 419,954 列中有 1,357 列缺首個時間；這些列不能進入「已完成且可計算首次回應時間」的分母。缺失不代表從未 resolved；首次 non-NMR 也不等於首次 Helpful。
- Coverage 的分母必須先指定 feed 與時間窗，再計算 distinct eligible tweetId；ineligible 與 unknown 不可混為一類。本次僅檢查各 feed 狀態分布，未指定最終分析分母。

## 可疑值與未解問題

下表為旗標事件數，同一列可能出現多個事件，不能直接相加當作可疑列數。所有列均保留。技術驗證通過表示按既定規則保留／標記，不表示資料已無疑點。

| 資料表 | 旗標事件 | 不同的可疑資料列 |
|---|---|---|
| batSignals | 9 | 5 |
| notes | 4 | 4 |
| ratings | 13 | 13 |
| noteStatusHistory | 2,175,237 | 2,174,994 |
| userEnrollment | 549 | 549 |

| 資料表 | 規則 | 事件數 | 處理 |
|---|---|---|---|
| batSignals | sourceLinks:invalid_source_url | 5 | 保留原始值與紀錄；未推測修正 |
| batSignals | suggestions:invalid_nested_url | 4 | 保留原始值與紀錄；未推測修正 |
| notes | classification:missing_classification | 2 | 保留原始值與紀錄；未推測修正 |
| notes | summary:blank_text | 2 | 保留原始值與紀錄；未推測修正 |
| ratings | suggestion:blank_text | 13 | 保留原始值與紀錄；未推測修正 |
| noteStatusHistory | timestampMillisOfNmrDueToMinStableCrhTime:unverified_minus_one_semantics | 2,173,762 | 保留原始值與紀錄；未推測修正 |
| noteStatusHistory | timestampMillisOfFirstNmrDueToMinStableCrhTime:unverified_minus_one_semantics | 118 | 保留原始值與紀錄；未推測修正 |
| noteStatusHistory | timestampMillisOfFirstNonNMRStatus:resolved_missing_history | 1,357 | 保留原始值與紀錄；未推測修正 |
| userEnrollment | timestampOfLastEarnOut:earnout_count_disagreement | 547 | 保留原始值與紀錄；未推測修正 |
| userEnrollment | timestampOfLastStateChange:invalid_timestamp | 1 | 保留原始值與紀錄；未推測修正 |
| userEnrollment | timestampOfLastStateChange:suspicious_timestamp_range | 1 | 保留原始值與紀錄；未推測修正 |

- 兩個 NMR 穩定時間欄位的 `-1` 真實語意尚未確認。
- Enrollment 有無效時間、可疑範圍時間及 earn-out 計數矛盾。疑似秒／毫秒問題尚無足夠依據，不自行乘 1000。
- 異常 URL 只標記；未自動修復前綴。缺失分類與缺失歷史不能用其他欄位猜補。

## 關聯驗證

直接重算原始粒度的 LEFT JOIN，並檢查右側唯一性。Notes → Requests、Ratings → Notes、作者／評分者 → Enrollment 為 many-to-one；Notes ↔ Status 的 noteId 為 one-to-one。Requests → Notes 是 one-to-many，因此「是否有 Note」先以 distinct tweetId 建立 lookup；評分明細也先聚合到 Note 粒度才能安全接到 Notes。

| 關聯 | 輸入列數 | 合併後列數 | 匹配 | 未匹配（含不可用鍵） | 其中不可用左鍵 |
|---|---|---|---|---|---|
| notes_requests | 3,137,735 | 3,137,735 | 170,383 | 2,967,352 | 8 |
| notes_status | 3,137,735 | 3,137,735 | 2,897,146 | 240,589 | 0 |
| status_notes | 3,343,818 | 3,343,818 | 2,897,146 | 446,672 | 0 |
| notes_authors | 3,137,735 | 3,137,735 | 3,137,735 | 0 | 0 |
| ratings_notes | 235,530,477 | 235,530,477 | 212,762,691 | 22,767,786 | 0 |
| ratings_raters | 235,530,477 | 235,530,477 | 235,530,477 | 0 | 0 |
| requests_notes | 487,851 | 487,851 | 111,372 | 376,479 | 0 |

未匹配紀錄都保留，未視為錯誤或自動刪除。快照範圍、刪除與時間先後可能影響匹配；本次不能斷言其原因。Notes/Status 的一致性及評分先後檢查只適用於成功匹配者；未匹配者不能因旗標值為 false 就被當作已通過時間檢查。

## 五筆人工核對

請先完成 [manual_cases.md](manual_cases.md) 的五筆原始紀錄，寫出預期結果與理由。案例涵蓋五個資料集、包含困難值；未提供個案清理後結果。你完成後才進行逐筆答案比對。

## 尚未完成／無法確認

1. 使用者對五筆原始紀錄的預期與理由，以及後續實際結果比對。
2. 模糊 sentinel、疑似時間單位、earn-out 矛盾的來源語意與處置判斷。
3. 專題 feed、觀察窗、截止日與 cohort 選擇，及依這些定義計算的 Coverage／Response Time。
4. 原始跨表未匹配的實際原因；現有快照無法單獨證明。

沒有自行修改清理規則或針對以上疑點新增排除規則。

## 既有主要轉換的變更核對

這些是先前清理階段的變更，本次驗證沒有重新清理。原始 profile 階段無變更；typing/sentinel/normalization 合併階段的變更如下。Changed cells 包含字串到布林／整數的型態轉換，不代表等量資訊被修改或遺失。稽核欄位與 companion 是新增欄，列數不變。

| 資料表 | 來源欄數 | 輸出欄數 | 發生型態／值轉換的列 | 轉換儲存格 | 與原報告吻合 |
|---|---|---|---|---|---|
| batSignals | 7 | 22 | 487,851 | 1,951,404 | 是 |
| notes | 24 | 31 | 3,137,735 | 59,932,092 | 是 |
| ratings | 35 | 42 | 235,530,477 | 6,833,041,562 | 是 |
| noteStatusHistory | 24 | 40 | 3,343,818 | 55,705,813 | 是 |
| userEnrollment | 8 | 16 | 1,497,640 | 7,488,200 | 是 |

重複處理階段：排除 0。關聯旗標階段：所有列數不變。彙總階段：ratings 改為每 Note 一列，所有 rating_count 可加總回原表，詳見上述列數說明。

四個 feed 的全部資格狀態（尚未加上時間窗／截止日）：

| Feed 欄位 | eligible | ineligible | unknown |
|---|---|---|---|
| noteRequestFeedEligibleAtMillis | 28,597 | 459,254 | 0 |
| apiSmallFeedEligibleAtMillis | 28,964 | 458,887 | 0 |
| apiLargeFeedEligibleAtMillis | 168,583 | 319,268 | 0 |
| apiXlFeedEligibleAtMillis | 487,506 | 345 | 0 |

## 重要總數前後比較

空字串轉 NULL 的類別以「缺失」對齊比較，不把這個儲存型態變更算成新增缺失。

| 資料表.欄位 | 值／缺失 | 原始數 | 清理數 | 差額 |
|---|---|---|---|---|
| ratings.version | 2 | 235,496,083 | 235,496,083 | 0 |
| ratings.version | 1 | 34,394 | 34,394 | 0 |
| ratings.helpfulnessLevel | HELPFUL | 144,595,094 | 144,595,094 | 0 |
| ratings.helpfulnessLevel | NOT_HELPFUL | 84,808,020 | 84,808,020 | 0 |
| ratings.helpfulnessLevel | SOMEWHAT_HELPFUL | 6,092,969 | 6,092,969 | 0 |
| ratings.helpfulnessLevel | 缺失（原始空字串／清理 NULL） | 34,394 | 34,394 | 0 |
| noteStatusHistory.currentStatus | NEEDS_MORE_RATINGS | 2,923,864 | 2,923,864 | 0 |
| noteStatusHistory.currentStatus | CURRENTLY_RATED_HELPFUL | 283,398 | 283,398 | 0 |
| noteStatusHistory.currentStatus | CURRENTLY_RATED_NOT_HELPFUL | 136,556 | 136,556 | 0 |
| notes.classification | NOT_MISLEADING | 615,593 | 615,593 | 0 |
| notes.classification | MISINFORMED_OR_POTENTIALLY_MISLEADING | 2,522,140 | 2,522,140 | 0 |
| notes.classification | 缺失（原始空字串／清理 NULL） | 2 | 2 | 0 |
