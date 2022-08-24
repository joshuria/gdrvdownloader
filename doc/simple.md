# Google Drive Exporter
本 repository 使用 Google Drive API v3 實作 Google Drive 匯出的功能。以下為支援的功能:
  - 可匯出所有的 Drive，包含 *我的雲端硬碟* 和 *共用雲端硬碟*
  - 可匯出 *與我共用* 內的檔案
  - 可匯出 *垃圾桶* 內的檔案
  - 可匯出 Google Docs
  - 將所有檔案輸出到 CSV
  - 下載時使用 gzip 減少流量
  - 下載後比對檔案完整性

其他類似的方法:
  - [Google Takeout](https://takeout.google.com/)
  - 使用 selenium 模擬人工流程的其他方法

> **注意**: Google Takeout 不能匯出 *共用雲端硬碟*、*與我共用*、和 *垃圾桶* 內的檔案。


# 需要的環境
  - 可開瀏覽器的桌面環境
  - Python 3.4+

## 可開瀏覽器的桌面環境

Google API 使用時需要經過授權，過程中會開網頁要求使用者登入和同意 app 使用需要的權限。 

## Python 3.4+

> **注意**: 不支援 Python 2.x

Python 可以在 *cmd*/*terminal*/*console* 上使用 `python -V` 或者 `python3 -V` 來檢查系統上安裝的版本，一般來
說 Linux 上會有已經裝好的版本，只需注意版本是不是 **3.4** 以上；Windows 上需要在
[Python Official Site](https://www.python.org/downloads/) 裡下載並安裝。另外在還沒安裝過的 Windoes 10+ 系
統上會把 `python`指令對應到 *Windows Store* 上的 python 讓使用者安裝，建議不要用 *Windows Store* 上的版本。

MacOS 可以使用 homebrew/port，相關文章很多，這裡不多說。

```sh
# brew
brew install python3
# port
sudo port install python3
```

不管在哪個系統上，安裝完成後記得檢查一下系統 `PATH` 環境變數裡能找到安裝的 python，而且在 console 上能出現像是:

```sh
$ python -V    # Output: Python 3.x.x
$ pip -V       # Output: pip a.b.c from <a path> (python 3.x.x)
```

# 使用方式
## 流程
整體使用流程說明如下:

  1. 使用 Git **clone** 下這個 repository，或者使用網頁上的下載功能下載這個 repository。
  1. 準備好自己的 *Google API credentials*，詳細請看 [新增 Api Credential](apiCredential.md)，請記得要把
    下載下來的 credentials 改名為 `client_secrets.json` 並且放到 clone 下來 repository 所在的位置。
  1. 開啟 console 設定環境:

        ```sh
        # 我是註解，前面 $ 代表是使用一般使用者帳號，忽略不要管他
        # python/pip 視自己系統情況改成 pip3/python3
        # 安裝 VirtualEnv
        $ pip install --user virtualenv
        # 換目前工作目錄到之前下載 / Clone repository 的位置 
        $ cd <repository path>
        # 建立 virtual environment
        $ python -m venv .venv
        # 啟用 virtual environment, Windows 請去掉前面的 source
        $ source .venv/bin/activate
        # 使用 pip 安裝需要的 packages
        $ pip install -r requirements.txt
        ```

  1. 開使執行

        ```sh
        $ python gdexporter.py -u 要處理的帳號
        # 如果也要下載 *與我分享* 的檔案
        $ python gdexporter.py -u 要處理的帳號 --sharedType both
        # 如果要忽略某些共用雲端硬碟
        $ python gdexporter.py -u 要處理的帳號 --ignoreDrive 硬碟名稱1 "有空白 硬碟名稱 2"
        ```