# 修正版使用步骤

这是覆盖更新包，不包含大型原始数据或完整清理后 CSV。不要删除原来的 coverage_assignment 文件夹。

1. 将包内 coverage_assignment 的内容合并到原文件夹，替换同名文件，保留原有 data/raw 和 coverage_cleaned.csv。
2. 阅读 validation/expected_records.json 中五笔固定预期及理由。这些是初次运行后的补充验证，不宣称事先写于初次清理之前。
3. 在原来的 coverage_assignment 终端运行：

```bash
python3 verify_submission.py
```

脚本检查原始文件哈希，重新扫描五个 Notes 文件，核对五笔预期、样本和完整清理后结果。需要几分钟，但不会重新跑两遍整个清洗。出现 PASS 后报告会自动更新。报错时不要把检查标为完成；保留报错信息。

4. 打开 notebooks/cleaning.ipynb。使用已有 Python 环境，运行第一个代码单元格（设置 ROOT），再运行最后一个代码单元格（显示最新报告），Command+S 保存。不需要 Run All。
5. 完成 GitHub commit 和 push 后，将代码提交 ID 填入 SUBMISSION_METADATA.json 的 commit_id 引号内，运行 python3 make_report.py，再刷新 notebook 最后单元格并保存。报告引用上一笔代码提交是正常的，不需要追求包含自身 commit ID。

下载日期未知仍标为 Unresolved。若能找到真实获取日期再补充，不要把报告日期当成下载日期。GitHub 未 push、补充验证未运行以及学生手工复核未完成的部分均不冒写完成。

如果 python3 提示缺少 reportlab 或 pandas，先在同一终端运行：

```bash
python3 -m pip install -r requirements.txt
```

最终向分支复制时包括 validation/、SUBMISSION_METADATA.json、verify_submission.py 及原有代码、报告、样本和小型证据。不要复制原始 TSV。
