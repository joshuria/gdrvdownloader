# Google Drive Exporter
Export your Google Drive by Google Drive API v3.

This implementation supports:
  - Export all drives, include *My Drive* and other shared drives.
  - Export all files in *Shared with me*.
  - Export all files in trash.
  - Support Google Docs export.
  - Export all files (include folder, files, links) to CSV.
  - Use gzip when downloading.
  - Checking file integrity after download.
  - Prevent unnecesary download if file alread exists and matches.

Other approach to export Google Drive:
  - [Google Takeout](https://takeout.google.com/)
  - Other implementations based on selenium.

> **Note**: Google Takeout does not allow you export Shared Drives and file in *Shared with me* and
> trashed files.

程式新手請看[簡單使用法](doc/simple.md)。


# Requirement
  - Graphical environment
  - Python 3.4+
  - Other dependencies please refer to [requirements.txt](requirements.txt).
  - (Optional) VirtualEnv

# Usage
## Step

  1. Clone this repository.
   
  2. Generate you own Google API credential for Google Drive.  
    We require the following region:
      - https://www.googleapis.com/auth/drive.metadata.readonly
      - https://www.googleapis.com/auth/drive.readonly

  3. Download the API credential, rename to `client_secrets.json`, save to repository root folder.

  4. *[Optional]* Create virtual environment.
      ```sh
          # Install virtual env
          pip install virtualenv
          # Create venv environment
          python -m venv .venv
          # Activate this environment
          source .venv/bin/activate
      ```

  5. Install necessary package.
      ```sh
          pip install -r requirements.txt
      ```

  6. Execute.
      ```sh
          python gdexport.py -u <your account>
      ```

## Keywords Definition
  - *<USER_ACCOUNT>*: user account specified in command line option `-u`.
  - *<DRIVE_NAME>*: name of drive or shared drive. Account default drive *My Drive* is called
      **MyDrive** in this application.
  - *<OUTPUT_ROOT_PATH>*: root of output folder pecified by command line option `-o`.
  - *<FILEINFO_CSV>*: CSV files stores all queried file information of specific *<DRIVE_NAME>*.

## All Options:

  - `-h`, `--help`: show simple help message.
  - `-u <USER_ACCOUNT>`, `--user <USER_ACCOUNT>`: **Required** user account to export.
  - `--downloadOnly`: ignore fetching files from server and use previous fetched file info CSV.
        This option is for retrying previous failed files.
  - `--fileInfoCsv FILEINFO_CSV`: manually give *<FILEINFO_CSV>* as file info. This option also
      enable `--downloadOnly` and ignore `--sharedType`. The drive name and ID are retrieved from
      *<FILEINFO_CSV>*.
      
      > User account who generates *<FILEINFO_CSV>* is assumed matches to given authed
      > *<USER_ACCOUNT>*.
  - `--includeTrashed`: also include trashed files.

      > Note that trashed files will be put in
      > `<OUTPUT_ROOT_PATH>/<USER_ACCOUNT>/<DRIVE_NAME>-Trash`.
  - `--ignoreDrive DRIVE_A DRIVE_B ...`: drive name to be ignored. Use **MyDrive** for account
        personal drive (*My Drive* in Google drive page). This option is useful in GSuite, G2, or
        Google Workspace shared drives.
  - `-j N`, `--job N`: the number of concurrent download jobs. Default is 8.
  - `--maxRetry N`: max number of download retyr. Default is 3.
  - `--noMd5`: skip file MD5 checksum verification.
  - `-o <OUTPUT_ROOT_PATH>`, `--output <OUTPUT_ROOT_PATH>`: output root path. Default value is
      `./output`.  

      > Exported files will put in `OUTPUT_ROOT_PATH/USER_ACCOUNT/Drive_Name`.
  - `--sharedType {shared, owned, both}`: specify shared files to export or not. This option is
      ignored when fetching files from shared drives. Default is **owned**.
      * **shared**: only export shared files, i.e. only files in *Shared with me* will be exported.
      * **owned**: only files owned by *<USER_ACCOUNT>* will be exported.
      * **both**: both shared and account owned files will be exported.

      > **Note**: file shared by others will be put in
      `<OUTPUT_ROOT_PATH>/<USER_ACCOUNT>/<DRIVE_NAME>-Shared`.

      > **Warning**: this parameter is ignored when exporting shared drives due to limitation of
      > Google Drive API.


## Sample Usage
### Normal use:
This will export drive owned by `my.account@g2.school.edu` with only owner is *me* files by
*4* download jobs.

```sh
    python gdexporter.py -u my.account@g2.school.edu -j 4
```

### Download with shared files:
This will export drive owned by `my.account@g2.school.edu` with both shared and owned files by
**4** download jobs.

```sh
    python gdexporter.py -u my.account@g2.school.edu -j4 --sharedType both
```

### Retry previous failed export:
This will checking and download owned by `my.account@g2.school.edu` only owner is *me* files by
**4** download jobs.

```sh
    python gdexporter.py -u my.account@g2.school.edu --downloadOnly -j4
```

## Output Folder Structure
Assume user account has *My Drive* and 1 shared drive with name *ShareDriveA*, output folder will
be:

```text
    <OUTPUT_ROOT>
        |--- <USER_ACCOUNT>
                |--- MyDrive.csv      # CSV for all files in My Drive
                |--- ShareDriveA.csv  # CSV for all files in ShareDriveA
                |--- MyDrive          # Folder for files in My Drive owned by "me", not trashed
                |       |--- <files>
                |--- MyDrive-Shared   # Folder for files in My Drive shared by others, not trashed
                |       |--- <files>
                |--- MyDrive-Trash    # Folder for files in My Drive but has been trashed
                |       |--- <files>
                |--- ShareDriveA      # Folder for files in ShareDriveA owned by "me", not trashed
                |       |--- <files>
                |--- ShareDriveA-Trash  # Folder for files in ShareDriveA but has been trashed
                |       |--- <files>
```

# Implementation
The entire export flow includes 3 main steps:

  1. **Auth**: request user allow this application to operate on target account. In this step, if
      this is the first time to auth *<USER_ACCOUNT>* given by command line options, system default
      browser will be opened and redirect to google login page (or account selection page). After
      login, the web page will show this application requires google drive read permissions.

      After auth, the auth token is saved to `tokens/<USER_ACCOUNT>.json`
      we uses authed information to query account information, includes user emain, quota, and
      shared drive list.

      > **Note:** we highly recommanded login user should be the same as *<USER_ACCOUNT>* in order
      > to prevent export fail caused by permission.

  2. **Fetch File Info and Check**: for each shared drives and *My Drive*, we fetch all files,
      folders with required filter such as `--includeTrashed`. For each file record, we check if
      there's the same file in output folder by **MD5** or file size and modified time. If match,
      the file will be marked as ignored to prevent unnecessary downloadin.
      
      These information records and checking results are stored into CSV file with *<DRIVE_NAME>* as
      file name under *<OUTPUT_ROOT_PATH>/<USER_ACCOUNT>*.

  3. **Download**: for each file marked as pending, we download concurrently. We check downloaded
      files by MD5 hash. For each failed file, we will retry again.  

Final generated files are:
  * **<FILEINFO_CSV>**: for each *<DRIVE_NAME>* we generate one for it.
  * **fail.csv**: all failed files. Some files such as 3rd party app data requires user manually 
      export.
  * Downloaded files: these files are stored under `<OTUPUT_ROOT_PATH>/<USER_ACCOUNT>/<DRIVE_NAME>`.


# FAQ


# Limitation
  - [Google Drive API v3] the `--sharedType` is ignored when query files in shared drives. Add this
      filter the API will return just root folder and no files.
  - We do not handle file revision and always download the final version.
 

# Known Issues
  * [Coggle](https://coggle.it/) generated mind map files require manually export in Coggle.
  * We do not check if local system has enough disk space to store exported files.
  * Current rate limit handling is too simple (just sleep for a long while).
  * This implementation is not memory efficient.
