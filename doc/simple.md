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

## 可用選項

  - `-h`, `--help`: 顯示簡易說明。
  - `-u 使用者帳號`, `--u 使用者帳號`: **必填** 指定要處理的 Google 帳號。 $a
  - 
  - `--downloadOnly`: 只使用目前在 `輸出位置/使用者帳號` 內所儲存的檔案資訊 csv，重新檢查並下載檔案。這個選項可用在
    試下載上次失敗的檔案。
  - `--fileInfoCsv 檔案資訊.csv`: 指定存有所有要匯出檔案資訊的 CSV 位置。這個選項也同時會啟用 `--downloadOnly`，
    並且忽略 `--sharedType`。雲端硬碟的名稱和 ID 將會從這個檔案裡取得。

    > **注意**: 這個選項將會假設檔案所屬的使用者帳號和由 `-u` 指定的帳號相同，不會做其他的檢查。

  - `--ignoreDrive 硬碟名稱A 硬碟名稱B "有空白 硬碟名稱C" ...`: 要忽略的雲端硬碟名稱。如果不想匯出 *我的雲端硬碟*
    ，請使用 `--ignoreDrive MyDrive`。

  - `--includeTrashed`: 匯出時包含在垃圾桶裡的檔案。  

    > **注意**: 在垃圾桶裡的檔案將會儲存到 `輸出位置/使用者帳號/雲端硬碟名稱-Trashed` 裡。

  - `-j 平行下載檔案數量`, `--job 平行下載檔案數量`: 最大可同時下載的檔案數量，預設值為 8 。
  - `--maxRetry 最大重試下載次數`: 最大下載重試次數，預設值 3。
  - `--noMd5`: 不檢查檔案 MD5。
  - `-o 輸出位置`, `--output 輸出位置`: 匯出的檔案會儲存到這個路徑底下，預設值是 `./output`。

    > 實際上會在這這位置對每個帳號和雲端硬碟名稱再開各別的資料夾，也就是說匯出的檔案會存在
    > `輸出位置/使用者帳號/雲端硬碟名稱` 裡。

  - `--sharedType {shared, owned, both}`: 指定是否要匯出別的帳號分享給自己的檔案，可選三個值，預設是
    **owned**。

    * **shared**: 只匯出 *從其他帳號分享給我* 的檔案。
    * **owned**: 只匯出 *擁有者是我* 的檔案。
    * **both**: 匯出所有檔案。

    > **注意**: 分享的檔案會被存在 `輸出位置/使用者帳號/雲端硬碟名稱-Shared`。

    > **注意**: 在處理 *共用雲端硬碟* 時，由於 Google Drive API 的限制，這個參數的設定會被忽略。

## 使用範例
### 一般使用
以下指令會將帳號 `my.account@g2.school.edu` 裡、擁有者是 *我*、不在垃圾桶裡的所有檔案匯出到
`./output/my.account@g2.school.edu` 裡，並且同時最多有 *4* 個檔案可平行下載。

```sh
    python gdexporter.py -u my.account@g2.school.edu -j 4
```

### 同時匯出自己與來自其他帳號分享的所有檔案
以下指令會將帳號 `my.account@g2.school.edu` 裡，包含 *與我分享* 在內，所有雲端硬碟裡不在垃圾桶裡的檔案全部匯出到
`./output/my.account@g2.school.edu` 裡，並且同時最多有 *4* 個檔案可平行下載。

```sh
    python gdexporter.py -u my.account@g2.school.edu -j 4 --sharedType both
```

### 使用前一次匯出的檔案資訊紀錄，單純檢查並下載紀錄中的檔案
以下指令將會檢查所有在 `./output/my.account@g2.school.edu/<雲端硬碟>.csv` 裡的匯出紀錄，檢查所有紀錄並下載缺少或
MD5 不相同的檔案。

```sh
    # 假設帳號 my.account@g2.school.edu 有名稱為 MyDrive, ShareDriveA, ShareDriveB 3 個雲端硬碟
    # 以下指令會使用
    #    - ./output/my.account@g2.school.edu/MyDrive.csv
    #    - ./output/my.account@g2.school.edu/ShareDriveA.csv
    #    - ./output/my.account@g2.school.edu/ShareDriveB.csv
    # 這 3 個 csv 內紀錄的檔案清單，檢查並下載所有檔案
    python gdexporter.py -u my.account@g2.school.edu --downloadOnly
```

## 輸出資料夾結構
假設使用者 `my.account@g2.school.edu` 有 *我的雲端硬碟* 和 1 個名稱為 *ShareDriveA* 的分享雲端硬碟，並且在匯出
時使用預設的輸出位置，輸出資料夾結構將會是:

```text
    output
        |--- my.account@g2.school.edu
                |--- MyDrive.csv      # 存有 "我的雲端硬碟" 所有檔案資訊的 CSV
                |--- ShareDriveA.csv  # 存有分享雲端硬碟 ShareDriveA 所有檔案資訊的 CSV
                |--- MyDrive          # 存有 "我的雲端硬碟" 內，擁有者是 "我"，而且不在垃圾桶內的檔案
                |       |--- <files>
                |--- MyDrive-Shared   # 存有 "我的雲端硬碟" 內，由其他人分享，而且不在垃圾桶內的檔案
                |       |--- <files>
                |--- MyDrive-Trash    # 存有 "我的雲端硬碟" 內，所有在垃圾桶內的檔案
                |       |--- <files>
                |--- ShareDriveA      # 存有分享雲端硬碟 ShareDriveA 內，所有不在垃圾桶內的檔案
                |       |--- <files>
                |--- ShareDriveA-Trash # 存有分享雲端硬碟 ShareDriveA 內，所有在垃圾桶內的檔案 
                |       |--- <files>
```


# 限制
  - `--sharedType` 在處理分享雲端硬碟時會被忽略，因為 Google Drive 架構上在鈩享雲端硬碟內的檔案擁有者是所屬機構的
    管理者，檔案都會是被分享的。因此 Google Drive API 在查尋分享雲端硬碟內的檔案時，不支援這個篩選條件。
  - 我們不處理檔案的版本，只會下載檔案最新的版本。


# 已知問題
  * [Coggle](https://coggle.it/) 的檔案不能被 API 匯出，必須使用者自行到 Coggle 內處理。
  * 我們沒有檢查目前系統上的可用硬碟空䦔是否足夠下載所有檔案。
  * 目前針對 Google Drive API rate limit 的處理太過簡單。
  * 目前實作的方式可能會占用比較多的記憶體。
  