# Google Drive Exporter
本 repository 使用 Google Drive API v3 實作 Google Drive 匯出的功能。以下為支援的功能:
  - 可匯出所有的 Drive，包含 *我的雲端硬碟* 和 *共用雲端硬碟*
  - 可匯出 *與我共用* 內的檔案
  - 可匯出 *垃圾桶* 內的檔案
  - 將所有檔案輸出到 CSV
  - 下載時使用 gzip 減少流量
  - 下載後比對檔案完整性

其他類似的方法:
  - [Google Takeout](https://takeout.google.com/)
  - 使用 selenium 模擬人工流程的其他方法

> **注意**: Google Takeout 不能匯出 *共用雲端硬碟*、*與我共用*、和 *垃圾桶* 內的檔案。