# QuickEye Analyzer

用於快速載入 S2P／S4P 通道資料，搭配 AEDT Circuit 進行 Eye Analysis，協助工程師快速檢視高速訊號品質。

## 主要功能

- 支援 Single-Ended 與 Differential 通道分析。
- 自動計算 UI 與建議 rise time。
- 選擇輸入通道檔案與輸出資料夾。
- 連接 AEDT Circuit 並執行分析流程。

## 使用環境

- Ansys Electronics Desktop（含 Circuit）
- Python 3
- PyAEDT：`pip install pyaedt`

## 使用方式

```text
python QuickEye_Analyzer.py
```

依 GUI 選擇 S2P／S4P 檔案、設定訊號速度與輸出資料夾後執行分析。

## 公開範圍

Repository 只保留腳本與脫敏後的範例資料。實際通道模型與客戶資料請勿直接上傳。

如需自動化報表、批次通道分析或 AEDT 流程整合，請來信洽詢。

---

本 Repository 為 Jeff Hong 個人技術作品集之公開展示內容，非 Taiwan Auto-Design Co.（TADC，虎門科技）官方帳號，亦非 Ansys, Inc. 官方合作項目；Ansys、HFSS、SIwave 為 Ansys, Inc. 之商標。原始碼與內容僅供技術展示，未經授權不得商業使用、散布或製作衍生作品，詳見 [LICENSE](LICENSE)。如需授權或合作，請洽 jeff.hong@cadmen.com。
