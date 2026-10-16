# Member 2 交接說明

## 已完成
- 完整 dashboard 規格：DASHBOARD_SPEC.md，可整合到 BUILD_SPEC.md。
- 保留 Coverage 與 Response Time，改為分區篩選，不把筆記分類套到未涵蓋請求。
- 為每個指標定義資料、分母、時間窗、缺失處理、展示、互動及測試。
- 首次非 NMR 作為提案終點；明確區分筆記狀態與評分 helpfulness。
- 加入等待中數量、完整觀察窗、資料品質與抽樣提示。
- 將原本任意高低四象限改成描述性散點圖；不宣稱因果。
- 9 項具體驗收案例；只保留頁面配置、指標與圖表、篩選器、互動與特殊情況、驗收條件五部分。

## 開會必須確認
1. Member 5：Standard feed、7 天觀察窗、covered 定義及 cutoff 是否同意？
2. Member 6：首次非 NMR、history 缺失處理、前 24 小時評分活動是否同意？
3. Member 3/4：統一資料版本與可信觀察截止日是什麼？哪些時間或合併問題會影響畫面上的統計？
4. Member 1：單頁雙區塊與描述性 review priorities 是否符合願景？
5. 指定整合者並安排 fresh-agent test。這份交付沒有執行分析 backend 或 fresh-agent test。

## 更新圖怎麼使用
更新圖是設計示意，全部數字與日期為人工設計的 fixture，不是真實測量。真實 UI 日期要從經團隊確認的 snapshot cutoff 產生。生成圖中的文字若與 DASHBOARD_SPEC.md 有差異，以規格與 fixture 為準，先修正圖再用於正式展示。

建議介紹：我們保留 Phase 1 的單頁總覽，但把不同分析單位分開；Coverage 看請求，Response 看筆記，Helpfulness 看評分。所有率都顯示分母，並列出排除資料與觀察限制。

## 尚未聲稱完成
團隊規則簽核、main 合併、真實指標計算、效能測試、Phase 3 UI、完整 Phase 2 BUILD_SPEC.md 與 fresh-agent test。這些需要其他成員成果及共同決策。
