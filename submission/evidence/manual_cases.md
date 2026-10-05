# 五筆人工核對題：僅原始資料

以下五筆直接從本機原始 ZIP 讀取。沒有附上清理後數值、個案旗標結果或答案。
資料列號從標題後第一列起算為 1（TSV 實體行號 = 資料列號 + 1）。JSON 中所有欄位值都是原始字串；`""` 表示原始空字串。

請對每題寫下：①預期保留／轉換／新增／標記的內容，②適用規則與理由，③對列數或指標分母的影響。

填寫說明：以下預期由 Codex 依原始案例與 plan.md 協助草擬，供學生審閱確認；不代表學生已獨立完成判斷或已完成實際輸出核對。填寫時未讀取這五筆清理後的個案結果。

## 案例 1：batSignals

來源：`/Users/bobo/dso576/project/raw/communitynotes/data/batSignals-00000.zip` → `batSignals-00000.tsv`，資料列 **14,509**。
相關規則：plan.md §3.A：來源連結、各 feed 資格時間、巢狀 suggestions。

逐項判斷來源連結、四個資格時間與 suggestions 應如何保留、衍生或標記。

```json
{
  "tweetId": "2072527447862759726",
  "noteRequestFeedEligibleAtMillis": "-1",
  "apiSmallFeedEligibleAtMillis": "-1",
  "apiLargeFeedEligibleAtMillis": "1784756989691",
  "apiXlFeedEligibleAtMillis": "1784756989691",
  "sourceLinks": "yuujihttps://x.com/animejujutsu/status/2029846970714706335",
  "suggestions": "[{\"suggestion_id\":2080047309124174174,\"suggestion\":\"the character's name has been incorrectly translated to Geto Suguru instead of Yuuji\",\"source_link\":\"Yuujihttps://x.com/animejujutsu/status/2029846970714706335?s=20\"}]"
}
```

你的預期結果：保留整筆 request 與原始值；tweetId 保持字串。sourceLinks 衍生為依逗號分隔、去除各項前後空白的清單；本例只有一項，保留 yuuji 前綴並標記網址格式異常，不擅自修復。四個 feed 獨立處理：noteRequestFeedEligibleAtMillis 與 apiSmallFeedEligibleAtMillis 的 -1 對應無資格日期及 ineligible 狀態，原始 -1 可追溯；apiLargeFeedEligibleAtMillis 與 apiXlFeedEligibleAtMillis 的 1784756989691 依毫秒轉成相同的 UTC 衍生日期，不推定 feed 間的包含關係。suggestions 解析為含一個物件的陣列，保留原始 JSON、文字、鍵及順序；suggestion_id 精確轉成字串 "2080047309124174174"，不經浮點數；source_link 保留原文並另外標記異常前綴。

理由與分母影響：依 plan.md §2、§3.A，異常網址不得造成整列刪除，-1 的意義必須按欄位解讀。總 request 筆數不變；若日後以標準或 small feed 的資格為分母，本例不納入；若以 large 或 XL feed 為準，仍需依明確的觀察期間等條件判斷。有效網址分析須另外記錄異常連結的排除範圍，不能連帶刪除 request 或 suggestion。本階段不選定 feed 或最終分析分母。

實際結果與證據位置：已在 `data/cleaning_run/cleaned/batSignals/batSignals-00000.parquet` 以 `_source_file=batSignals-00000.zip`、`_source_member=batSignals-00000.tsv`、`_source_row=14509` 找到對應列。清理後 `tweetId="2072527447862759726"`；`sourceLinks_list=["yuujihttps://x.com/animejujutsu/status/2029846970714706335"]`；`suggestions_parsed` 中 `suggestion_id` 為字串 `"2080047309124174174"` 且 `source_link` 保留 `Yuuji` 前綴。`noteRequestFeedEligibleAtMillis=-1` 與 `apiSmallFeedEligibleAtMillis=-1` 的 UTC companion 為 `NULL`、狀態為 `ineligible`；`apiLargeFeedEligibleAtMillis` 與 `apiXlFeedEligibleAtMillis` 轉為 `2026-07-22 21:49:49.691000+00:00`、狀態為 `eligible`。異常標記見 `data/cleaning_run/audit/batSignals-00000-flags.parquet` 同一來源列：`sourceLinks: invalid_source_url`，決策為保留異常 URL token、不修復；`suggestions: invalid_nested_url`，決策為保留原始 `source_link`、不修復。

是否符合預期：符合。

差異、可能原因或待釐清：未見實質差異。實際輸出把 feed 原始毫秒欄位存為整數、UTC companion 另存；網址異常以 audit flags 記錄，未刪列也未修復，與預期一致。

## 案例 2：notes

來源：`/Users/bobo/dso576/project/raw/communitynotes/data/notes-00002.zip` → `notes-00002.tsv`，資料列 **114**。
相關規則：plan.md §3.B：classification、tweetId、summary、isCollaborativeNote。

判斷空白分類、識別欄位、文字與 collaborative 註記的處理；說明是否保留此列。

```json
{
  "noteId": "2014121093532098991",
  "noteAuthorParticipantId": "F75B04680623CD9A452496D4AB69A20ED730CE93652C7113175BC7AA82AFEF23",
  "createdAtMillis": "1769038944674",
  "tweetId": "-1",
  "classification": "",
  "believable": "",
  "harmful": "",
  "validationDifficulty": "",
  "misleadingOther": "0",
  "misleadingFactualError": "0",
  "misleadingManipulatedMedia": "0",
  "misleadingOutdatedInformation": "0",
  "misleadingMissingImportantContext": "0",
  "misleadingUnverifiedClaimAsFact": "0",
  "misleadingSatire": "0",
  "notMisleadingOther": "0",
  "notMisleadingFactuallyCorrect": "0",
  "notMisleadingOutdatedButNotWhenWritten": "0",
  "notMisleadingClearlySatire": "0",
  "notMisleadingPersonalOpinion": "0",
  "trustworthySources": "0",
  "summary": "The statement '1+1 actually equals to 3' is false in standard arithmetic, where 1+1=2. It may refer to metaphorical synergy in business or relationships, meaning combined effects exceed the sum of parts. However, mathematically it remains incorrect. https://en.wikipedia.org/wiki/1+1 https://www.scirp.org/journal/paperinformation?paperid=73964",
  "isMediaNote": "0",
  "isCollaborativeNote": "1"
}
```

你的預期結果：保留此 note。noteId 與作者識別碼保持字串；tweetId 的原始 -1 保持可追溯，供合併使用的值標為不可用並附 sentinel 註記，不能用 -1 與其他列互相匹配。classification 空字串轉為缺失並標記，不根據 summary、collaborative 狀態或全零原因欄位猜測分類。believable、harmful、validationDifficulty 的空字串維持缺失。各二元欄位依 0→false、1→true 轉換，因此原因欄位與 trustworthySources 為 false、isMediaNote 為 false、isCollaborativeNote 為 true。summary 原文完整保留，另產生只修剪前後空白的文字；本例顯示的文字無前後空白，預期衍生文字相同，不刪除網址、不改大小寫。createdAtMillis 按毫秒新增 UTC 日期。

理由與分母影響：依 plan.md §2、§3.B，缺失分類及無可用貼文 ID 不使筆記本身失效；全零原因也不能推斷分類。總 note 筆數不變，仍可用於適用的 note 層級或 collaborative 分析；不能用本列的 tweetId 參加貼文 ID 合併。分類比例若只計有效分類，本例不入該分母並另報缺失數；若呈現所有筆記，則另列未知分類，明確交代口徑。

實際結果與證據位置：已在 `data/cleaning_run/cleaned/notes/notes-00002.parquet` 以 `_source_file=notes-00002.zip`、`_source_member=notes-00002.tsv`、`_source_row=114` 找到對應列。清理後 `noteId` 與 `noteAuthorParticipantId` 保留為字串；`tweetId=NULL`；`classification=NULL`、`believable=NULL`、`harmful=NULL`、`validationDifficulty=NULL`；`isMediaNote=false`、`isCollaborativeNote=true`；`summary` 與 `summary_trimmed` 相同，網址與大小寫未改；`createdAtMillis_utc=2026-01-21 23:42:24.674000+00:00`。異常標記見 `data/cleaning_run/audit/notes-00002-flags.parquet` 同一來源列：`classification: missing_classification`，決策為保留 note、分類未知、不補值。

是否符合預期：符合。

差異、可能原因或待釐清：清理後供合併使用的 `tweetId` 實際儲存為 `NULL`，符合「不可用且不能用 -1 合併」的預期；原始 `-1` 需透過來源列重建/roundtrip 與 provenance 追溯，未見額外的 tweetId sentinel flag。其他欄位與預期一致。

## 案例 3：ratings

來源：`/Users/bobo/dso576/project/raw/communitynotes/data/ratings-00000.zip` → `ratings-00000.tsv`，資料列 **1**。
相關規則：plan.md §3.C：分開新舊評分格式、helpful/notHelpful、helpfulnessLevel。

判斷舊版 helpful 與空白 helpfulnessLevel 的處理；說明此列是否進入 helpfulnessLevel 比例的分母。

```json
{
  "noteId": "1352796878438424576",
  "raterParticipantId": "6BC15A6669481F9CEF45602263C22A860662F750EF683F326BB9B3535B0B740D",
  "createdAtMillis": "1611860252442",
  "version": "1",
  "agree": "1",
  "disagree": "0",
  "helpful": "1",
  "notHelpful": "0",
  "helpfulnessLevel": "",
  "helpfulOther": "0",
  "helpfulInformative": "1",
  "helpfulClear": "1",
  "helpfulEmpathetic": "1",
  "helpfulGoodSources": "1",
  "helpfulUniqueContext": "1",
  "helpfulAddressesClaim": "0",
  "helpfulImportantContext": "0",
  "helpfulUnbiasedLanguage": "0",
  "notHelpfulOther": "0",
  "notHelpfulIncorrect": "0",
  "notHelpfulSourcesMissingOrUnreliable": "0",
  "notHelpfulOpinionSpeculationOrBias": "0",
  "notHelpfulMissingKeyPoints": "0",
  "notHelpfulOutdated": "0",
  "notHelpfulHardToUnderstand": "0",
  "notHelpfulArgumentativeOrBiased": "0",
  "notHelpfulOffTopic": "0",
  "notHelpfulSpamHarassmentOrAbuse": "0",
  "notHelpfulIrrelevantSources": "0",
  "notHelpfulOpinionSpeculation": "0",
  "notHelpfulNoteNotNeeded": "0",
  "ratedOnTweetId": "-1",
  "ratingSourceBucketed": "DEFAULT",
  "suggestion": "",
  "suggestionId": "-1"
}
```

你的預期結果：保留這筆舊版評分，保留 helpful=1、notHelpful=0 所表達的原始資訊；不根據舊版二元欄位推測補填 helpfulnessLevel，該欄位維持缺失。此處描述預期語意，實際儲存型態待比對確認。

理由與分母影響：依 plan.md §3.C，新舊評分格式分開處理，避免將舊版二元評分推測成新版分類。此列不刪除，因此仍計入總評分筆數；但不納入以非缺失 helpfulnessLevel 為基礎的比例分母。若另行分析舊版 helpful／notHelpful，應分開定義並報告其有效分母。

實際結果與證據位置：已在 `data/cleaning_run/cleaned/ratings/ratings-00000.parquet` 以 `_source_file=ratings-00000.zip`、`_source_member=ratings-00000.tsv`、`_source_row=1` 找到對應列。清理後 `noteId`、`raterParticipantId` 保留為字串；`version=1`；`agree=true`、`disagree=false`、`helpful=true`、`notHelpful=false`；`helpfulnessLevel=NULL`；`ratedOnTweetId=NULL`；`suggestion=""`、`suggestion_trimmed=""`；`suggestionId=NULL`；`createdAtMillis_utc=2021-01-28 18:57:32.442000+00:00`。此列在 `data/cleaning_run/audit/ratings-00000-flags.parquet` 未查到個別 flag。

是否符合預期：符合。

差異、可能原因或待釐清：實際儲存型態已確認：舊版二元欄位轉為 boolean，`helpfulnessLevel` 不由 `helpful=true` 補填而維持 `NULL`。`ratedOnTweetId=-1` 與 `suggestionId=-1` 實際轉為 `NULL`，與不可用 sentinel 的語意相符；因本案例預期主要關注 helpfulnessLevel 分母，未見需修正預期的差異。

## 案例 4：noteStatusHistory

來源：`/Users/bobo/dso576/project/raw/communitynotes/data/noteStatusHistory-00000.zip` → `noteStatusHistory-00000.tsv`，資料列 **595**。
相關規則：plan.md §3.D：timestampMillisAbovePcrhThreshold、timestampMinuteOfFinalScoringOutput。

判斷有符號 PCRH 值代表的處理方式與時間單位；區別 scoring-minute 中繼資料與事件時間。

```json
{
  "noteId": "1354945306908045315",
  "noteAuthorParticipantId": "441115D2D98CE13022445035D1FA1CD24F4E208C9CE2795B6CA2B8495BDAEE20",
  "createdAtMillis": "1611879109492",
  "timestampMillisOfFirstNonNMRStatus": "",
  "firstNonNMRStatus": "",
  "timestampMillisOfCurrentStatus": "1790139084069",
  "currentStatus": "NEEDS_MORE_RATINGS",
  "timestampMillisOfLatestNonNMRStatus": "",
  "mostRecentNonNMRStatus": "",
  "timestampMillisOfStatusLock": "1674003109873",
  "lockedStatus": "NEEDS_MORE_RATINGS",
  "timestampMillisOfRetroLock": "",
  "currentCoreStatus": "CURRENTLY_RATED_HELPFUL",
  "currentExpansionStatus": "CURRENTLY_RATED_HELPFUL",
  "currentGroupStatus": "",
  "currentDecidedBy": "NmrDueToMinStableCrhTime (v1.0)",
  "currentModelingGroup": "",
  "timestampMillisOfMostRecentStatusChange": "-1",
  "timestampMillisOfNmrDueToMinStableCrhTime": "-1",
  "currentMultiGroupStatus": "",
  "currentModelingMultiGroup": "",
  "timestampMinuteOfFinalScoringOutput": "29845679",
  "timestampMillisOfFirstNmrDueToMinStableCrhTime": "",
  "timestampMillisAbovePcrhThreshold": "-1788540132611"
}
```

你的預期結果：保留整列及所有原始值。timestampMillisAbovePcrhThreshold=-1788540132611 保留有符號整數；依既定編碼，另以絕對值 1788540132611 毫秒產生 UTC 日期，並衍生 no-longer-above-threshold 狀態，不當作普通缺失或直接轉為負 epoch 日期。timestampMinuteOfFinalScoringOutput=29845679 保留整數評分中繼資料，不按毫秒轉日期，也不當作筆記解決事件。currentStatus 保留 NEEDS_MORE_RATINGS，不能被 core／expansion 的 CURRENTLY_RATED_HELPFUL 覆蓋。空白 first／latest non-NMR 狀態和日期維持缺失，不從目前狀態或鎖定日期補填。MostRecentStatusChange=-1 對應無紀錄日期與獨立 sentinel 註記；NmrDueToMinStableCrhTime=-1 保留原值、日期為空並標記語意待確認，不能與空白 FirstNmrDueToMinStableCrhTime 混為一談。其餘可用正毫秒時間新增 UTC 日期，原值保持可追溯。

理由與分母影響：依 plan.md §3.D，PCRH 的符號包含狀態資訊，時間單位也依欄位而異，不能全域套用負數轉缺失或毫秒轉換。總 status 筆數不變，本例仍計入目前 NMR 狀態。缺少 first non-NMR 里程碑，不能計算已完成的首次 non-NMR 耗時，也不能斷言從未解決；若建立該指標，需單列此類不可計算紀錄，不納入已完成耗時平均的有效分母。

實際結果與證據位置：已在 `data/cleaning_run/cleaned/noteStatusHistory/noteStatusHistory-00000.parquet` 以 `_source_file=noteStatusHistory-00000.zip`、`_source_member=noteStatusHistory-00000.tsv`、`_source_row=595` 找到對應列。清理後 `currentStatus="NEEDS_MORE_RATINGS"`，`currentCoreStatus` 與 `currentExpansionStatus` 仍為 `CURRENTLY_RATED_HELPFUL`，沒有覆蓋目前狀態；`timestampMillisOfFirstNonNMRStatus=NULL`、`firstNonNMRStatus=NULL`。`timestampMillisAbovePcrhThreshold=-1788540132611` 保留有符號整數，UTC companion 為 `2026-09-04 16:42:12.611000+00:00`，`pcrh_state="no_longer_above"`。`timestampMinuteOfFinalScoringOutput=29845679` 保留為整數，未產生 `_utc` companion。正毫秒欄位已轉 UTC：`createdAtMillis_utc=2021-01-29 00:11:49.492000+00:00`、`timestampMillisOfCurrentStatus_utc=2026-09-23 04:51:24.069000+00:00`、`timestampMillisOfStatusLock_utc=2023-01-18 00:51:49.873000+00:00`。`timestampMillisOfMostRecentStatusChange=-1` 與 `timestampMillisOfNmrDueToMinStableCrhTime=-1` 的 UTC companion 均為 `NULL`；`timestampMillisOfFirstNmrDueToMinStableCrhTime=NULL`。異常標記見 `data/cleaning_run/audit/noteStatusHistory-00000-flags.parquet` 同一來源列：`timestampMillisOfNmrDueToMinStableCrhTime: unverified_minus_one_semantics`，決策為保留 `-1`、UTC companion 為空、語意未解。

是否符合預期：符合。

差異、可能原因或待釐清：未見實質差異。`timestampMillisOfMostRecentStatusChange=-1` 的日期 companion 為 `NULL`，但未在個別 audit flags 中另列；可能因規則已將該欄位的 `-1` 視為既定 sentinel，只對 `timestampMillisOfNmrDueToMinStableCrhTime` 這個語意未確認欄位另設 flag。

## 案例 5：userEnrollment

來源：`/Users/bobo/dso576/project/raw/communitynotes/data/userEnrollment-00000.zip` → `userEnrollment-00000.tsv`，資料列 **1,224,917**。
相關規則：plan.md §2、§3.E：timestampOfLastStateChange、可疑時間、不得擅改單位。

判斷時間值是否可疑、應如何標記與處理；區分有依據的轉換和推測性的修正。

```json
{
  "participantId": "D386CF31E993419F5075F102259605E9C38A04DFE7CD2B135A0692D037C69825",
  "enrollmentState": "earnedIn",
  "successfulRatingNeededToEarnIn": "31",
  "timestampOfLastStateChange": "1736527963",
  "timestampOfLastEarnOut": "1712159915303",
  "modelingPopulation": "CORE",
  "modelingGroup": "13.0",
  "numberOfTimesEarnedOut": "1"
}
```

你的預期結果：保留此參與者及原始 timestampOfLastStateChange=1736527963，先標記時間範圍可疑／單位待確認。依既定毫秒單位解讀會落在 1970 年，明顯需要調查，但不能僅因數字位數而自動改按秒讀取或乘以 1000。如產生按毫秒解讀的 UTC companion，必須保留品質標記，不能視為已驗證的有效事件時間；若後續判定不可用，需記錄理由並令供分析使用的值為空。不得用 timestampOfLastEarnOut 覆寫。timestampOfLastEarnOut=1712159915303 依毫秒新增 UTC 日期，不適用 sentinel=1；numberOfTimesEarnedOut 保留整數 1。modelingGroup 的精確整數表示 "13.0" 轉成整數 13，原值可追溯；successfulRatingNeededToEarnIn 轉成非負整數 31；participantId、earnedIn 與 CORE 保留。

理由與分母影響：依 plan.md §2、§3.E，疑似單位錯誤只有線索，沒有足夠證據可擅改；異常應先標記並保留供查證。總參與者筆數不變，仍可納入適用的狀態統計。需要可信 LastStateChange 日期的時間分析應先隔離此筆待確認值，明列受影響筆數及有效分母；不得把按毫秒換算的 1970 年日期無條件用於日期篩選或時間差。實際清理程式是否留有帶標記的 UTC 值，留待比對，不預先聲稱。

實際結果與證據位置：已在 `data/cleaning_run/cleaned/userEnrollment/userEnrollment-00000.parquet` 以 `_source_file=userEnrollment-00000.zip`、`_source_member=userEnrollment-00000.tsv`、`_source_row=1224917` 找到對應列。清理後 `participantId`、`enrollmentState="earnedIn"`、`modelingPopulation="CORE"` 保留；`successfulRatingNeededToEarnIn=31`、`modelingGroup=13`、`numberOfTimesEarnedOut=1`；`timestampOfLastStateChange=1736527963`，UTC companion 為 `1970-01-21 02:22:07.963000+00:00`；`timestampOfLastEarnOut=1712159915303`，UTC companion 為 `2024-04-03 15:58:35.303000+00:00`；`never_earned_out_consistent=false`。異常標記見 `data/cleaning_run/audit/userEnrollment-00000-flags.parquet` 同一來源列：`timestampOfLastStateChange: suspicious_timestamp_range`，決策為保留 timestamp 與 UTC 值、仍未解決，檢查時間不是分析 cutoff。

是否符合預期：符合。

差異、可能原因或待釐清：實際清理程式保留了按毫秒解讀的 1970 UTC companion，並以 `suspicious_timestamp_range` 標記未解，與「可追溯但不能視為已驗證事件時間」一致。未見用 `timestampOfLastEarnOut` 覆寫的情況；後續分析是否排除此 UTC companion 仍需依指標口徑待釐清。
