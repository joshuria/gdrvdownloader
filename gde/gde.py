# -*- coding: utf-8 -*-
import atexit
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from datetime import datetime
import itertools
import json
import os
from pprint import pprint
import time
from typing import Dict, List, Tuple
import pandas as pd
from tqdm.auto import tqdm
import colorama as color
from .config import Config
from .downloader import Downloader, DownloadTaskResult, _TaskStatus
from .file import FileInfo, FileType, md5
from .google import GoogleDriveClient


atexit.register(lambda: print(color.Style.RESET_ALL))
color.init()


def __fetchFileInfo(
    client: GoogleDriveClient, driveId: str, driveName: str, includeTrashed: bool,
    sharedType: str, cfg: Config
) -> Tuple[List[FileInfo], Dict[str, FileInfo]]:
    """Fetch file info from google drive.
    All file info will write to *fileInfo.csv* under given `outputRoot`.

     :param client: initialized GoogleDriveClient instance.
     :param outputRoot: output root folder.
     :param driveId: drive Id. Use emtpy string to fetch *My Drive*.
     :param includeTrashed: also fetch trashed files.
     :param cfg: config of this flow.
     :returns: Tuple of:
          - All fetched file info list.
          - All folder id to name mapping table.
    """
    totalCount = 0
    folderTable: Dict[str, FileInfo] = {}
    fileList: List[FileInfo] = []
    startTime = datetime.now()
    for files in client.queryFiles(
        driveId, trashed=includeTrashed, pageSize=cfg.queryFileInfoPageSize,
        sharedType=sharedType,
    ):
        for file in files:
            fileList.append(file)
            if file.fileType == FileType.FOLDER:
                folderTable[file.id] = file
        totalCount += len(files)
        print(f'Fetch {driveName} {totalCount} files...', end='\r')
    print(f'Fetch {driveName} {totalCount} files time: {datetime.now() - startTime}')
    return fileList, folderTable


def __checkFile(
    file: FileInfo, outputRoot: str, noMd5: bool, sharedType: str,
) -> Tuple[bool, Dict[str, str], FileInfo, int, int, int, int, int]:
    """Check if given file requires to download.
     :param sharedType: fetch files with owner filter.
        - both: include both shared with me and owned by me.
        - owned: only owned by me.
        - shared: only shared with me.
     :returns: tuple of:
        - Need download or not.
        - File as Dict.
        - FileInfo instance. The same as input parameter.
        - LinkCount, FolderCount, ExportCount, FileCount, NoChangeCount
    """

    def __toDict(file: FileInfo, action: str, status: str, message: str) -> Dict[str, str]:
        """Convert file info and action to dict."""
        d = file.asDict()
        d['exportLinks'] = json.dumps(file.exportLinks) if file.exportLinks else ''
        d['parents'] = json.dumps(file.parents) if file.parents else ''
        d['createdTime'] = file.ctime.isoformat()
        d['modifiedTime'] = file.mtime.isoformat()
        d['viewedByMeTime'] = file.atime.isoformat()
        d['action'] = action
        d['status'] = status
        d['message'] = message
        return d

    needDownload = False
    linkCount = 0
    folderCount = 0
    exportCount = 0
    fileCount = 0
    noChangeCount = 0
    # Check file type and status
    if file.fileType == FileType.LINK:
        linkCount += 1
        data = __toDict(file, 'Skip', 'Skip', 'File is Link')
    elif file.fileType == FileType.FOLDER:
        folderCount += 1
        data = __toDict(file, 'Skip', 'Skip', '')
    elif file.exportLinks:
        needDownload = True
        exportCount += 1
        data = __toDict(file, 'Export', 'Pending', 'Need export')
    else:
        fileCount += 1
        path = os.path.join(outputRoot, file.path)
        if (sharedType == 'owned') and (not file.owned):
            data = __toDict(file, 'Skip', 'Skip', 'File is shared but only export owned')
        elif (sharedType == 'shared') and file.owned:
            data = __toDict(file, 'Skip', 'Skip', 'File is owned by user but only export shared')
        elif os.path.exists(path) and os.path.isfile(path):
            if noMd5:
                stat = os.stat(path)
                if (stat.st_mtime == file.mtime.timestamp()) and \
                    (stat.st_atime == file.atime.timestamp()) and \
                    (stat.st_size == file.size):
                    data = __toDict(file, 'Skip', 'OK', 'File state match')
                    noChangeCount += 1
                else:
                    data = __toDict(file, 'Download', 'Pending', 'File state not match')
                    needDownload = True
            else:
                m = md5(path)
                if m != file.md5:
                    data = __toDict(file, 'Download', 'Pending', 'MD5 not match')
                    needDownload = True
                else:
                    data = __toDict(file, 'Skip', 'OK', 'MD5 match')
                    noChangeCount += 1
        else:
            data = __toDict(file, 'Download', 'Pending', 'Not exist')
            needDownload = True
    return needDownload, data, file, linkCount, folderCount, exportCount, fileCount, noChangeCount


def __fetchFileInfoFromCsv(
    csvPath: str, outputRoot: str, noMd5: bool, sharedType: str, includeTrashed: bool = False
) -> Tuple[List[FileInfo], pd.DataFrame]:
    """Fetch file info from existing CSV file.
    If the file does not exist, empty data frame will be returned.

     :param csvPath: path to CSV file to load.
     :param outputRoot: output root path.
     :param noMd5: skip MD5 check or not.
     :param sharedType: fetch files with owner filter.
        - both: include both shared with me and owned by me.
        - owned: only owned by me.
        - shared: only shared with me.
     :param includeTrashed: include trashed file or not.
     :returns: Tuple of:
          - File info list to download.
          - DataFrame stores all files.
    """
    df = pd.read_csv(csvPath, encoding='utf-8', keep_default_na=False)
    linkCount = 0
    noChangeCount = 0
    exportCount = 0
    fileCount = 0
    folderCount = 0
    downloadList = []
    startTime = datetime.now()

    # fileIter = map(lambda param: FileInfo(**param._asdict()), df.itertuples(index=False))
    fileIter = map(
        lambda v: FileInfo(**dict(zip(iter(df), iter(v)))),
        df.itertuples(index=False, name=None))
    with ThreadPoolExecutor() as executor:
        args = zip(
            fileIter,
            itertools.repeat(outputRoot), itertools.repeat(noMd5), itertools.repeat(sharedType))
        results = list(tqdm(
            executor.map(lambda param: __checkFile(*param), args),
            total=len(df),
            desc='Checking Files',
            ascii=True, dynamic_ncols=True))
    i = 0
    for result in results:
        needDownload, _, file, isLink, isFolder, isExport, isFile, isNoChange = result
        if (not includeTrashed) and file.trashed:
            noChangeCount += 1
            continue
        linkCount += isLink
        exportCount += isExport
        folderCount += isFolder
        fileCount += isFile
        noChangeCount += isNoChange
        if needDownload:
            downloadList.append((file, i))
        i += 1
    checkTime = datetime.now()
    # Save info of all files
    driveName = df['driveName'][0]
    driveId = df['driveId'][0]

    # Statistics
    print(f'Drive: {driveName} ({driveId})')
    print(f'Total files to download: {len(downloadList)}')
    print(f'Total normal files: {fileCount}')
    print(f'Total exported files: {exportCount}')
    print(f'Total no changed files: {noChangeCount}')
    print(f'Total folders: {folderCount}')
    print(f'Total links: {linkCount}')
    print('Time:')
    print(f'  - Check Time: {checkTime - startTime}')
    print('-' * 40)
    return downloadList, df


def __processFileInfo(
    outputRoot: str, fileList: List[FileInfo], folderTable: Dict[str, FileInfo], driveName: str,
    noMd5: bool, sharedType: str
) -> Tuple[List[Tuple[FileInfo, int]], pd.DataFrame]:
    """Process path of each files and dump to CSV.
     :param outputRoot: output root for saving CSV.
     :param fileList: fetched file info list.
     :param folderTable: table of all folders.
     :param driveName: drive name to be used as CSV file name.
     :param noMd5: skip MD5 file check or not.
     :param sharedType: fetch files with owner filter.
        - both: include both shared with me and owned by me.
        - owned: only owned by me.
        - shared: only shared with me.
    """
    def __updatePath(f: FileInfo, folderTable: Dict[str, FileInfo]) -> str:
        """Recursive update path by trace back parent."""
        # BC
        if f.path:
            return f.path
        if (f.name == '') or (len(f.parents) == 0):
            return driveName
        parent = folderTable[f.parents[0]]
        f.path = os.path.join(__updatePath(parent, folderTable), f.name)
        return f.path

    linkCount = 0
    noChangeCount = 0
    exportCount = 0
    fileCount = 0
    downloadList = []
    startTime = datetime.now()
    # Update file path
    for file in tqdm(fileList, desc='Update path', ascii=True, dynamic_ncols=True):
        __updatePath(file, folderTable)
        sharedPath = f'{driveName}-Shared'
        if not file.owned:
            if len(file.parents) == 0:
                # Shared in root folder
                file.path = sharedPath
            elif not file.path.startswith(sharedPath):
                # Shared file in other owned folder
                file.path = file.path.replace(driveName, sharedPath, 1)
        trashedPath = f'{driveName}-Trash'
        if file.trashed:
            if len(file.parents) == 0:
                # Deleted in root folder
                file.path = trashedPath
            elif not file.path.startswith(trashedPath):
                # Deleted file in other exist folder
                file.path = file.path.replace(driveName, trashedPath, 1)
    # Check
    with ThreadPoolExecutor() as executor:
        args = zip(
            iter(fileList),
            itertools.repeat(outputRoot), itertools.repeat(noMd5), itertools.repeat(sharedType))
        results = list(tqdm(
            executor.map(lambda param: __checkFile(*param), args),
            total=len(fileList),
            desc='Checking Files',
            ascii=True, dynamic_ncols=True))
    i = 0
    dictList = []
    for result in results:
        needDownload, data, file, isLink, _, isExport, isFile, isNoChange = result
        linkCount += isLink
        exportCount += isExport
        fileCount += isFile
        noChangeCount += isNoChange
        if needDownload:
            downloadList.append((file, i))
        dictList.append(data)
        i += 1
    checkTime = datetime.now()
    # Save info of all files
    df = pd.DataFrame(dictList)
    df['driveName'] = driveName
    df.to_csv(os.path.join(outputRoot, f'{driveName}.csv'), encoding='utf-8', index=False)
    pdTime = datetime.now()

    # Statistics
    print(f'Drive: {driveName} ({fileList[0].driveId})')
    print(f'Total files to download: {len(downloadList)}')
    print(f'Total normal files: {fileCount}')
    print(f'Total exported files: {exportCount}')
    print(f'Total no changed files: {noChangeCount}')
    print(f'Total folders: {len(folderTable.items())}')
    print(f'Total links: {linkCount}')
    print('Time:')
    print(f'  - Total Time: {pdTime - startTime}')
    print(f'  - Check Time: {checkTime - startTime}')
    print(f'  - To CSV Time: {pdTime - checkTime}')
    print('-' * 40)
    return downloadList, df


def __formatDesc(msg: str, status: _TaskStatus) -> str:
    """Format download task status for displaying on progress bar."""
    pathLength = 40
    if status is None:
        return msg.ljust(pathLength)[:pathLength]
    else:
        #msg = status.title.ljust(19) if len(status.title) < 19 else (status.title[:16] + '...')
        msg = status.title.ljust(pathLength)[:pathLength]
        if status.message:
            return f'[{status.message}] {msg} '
        elif status.total:
            # When downloading
            ratio = round(status.current / status.total * 100, 2)
            return f'{ratio:5.2f}% {msg}'
        else:
            # When requesting
            return f'[Request] {msg}'


def __updateResultMessage(
    result: DownloadTaskResult, dfTable: Dict[str, pd.DataFrame], canRetry: bool
) -> str:
    """Updatedownload result and generate message for printing."""
    timeLength = 8
    msgLength = 12
    path = os.path.join(result.file.path, result.file.name)
    duration = str(result.requestTime + result.downloadTime)\
        .split('.', maxsplit=1)[0]\
        .ljust(timeLength)
    fileId = result.file.id
    if result.result:
        # Success
        dfTable[result.file.driveId].loc[result.i, 'status'] = 'OK'
        dfTable[result.file.driveId].loc[result.i, 'message'] = ''
        return '🎉  ' + color.Fore.GREEN + f'{duration} ' + color.Fore.RESET + \
            'Success'.ljust(msgLength) + \
            color.Style.BRIGHT + color.Fore.BLUE + f'({fileId}) ' + color.Style.RESET_ALL + \
            color.Style.BRIGHT + f'{path}' + color.Style.RESET_ALL
    elif result.exception:
        # Fail with exception
        dfTable[result.file.driveId].loc[result.i, 'status'] = 'Fail'
        dfTable[result.file.driveId].loc[result.i, 'message'] = 'Unexpected exception'
        pprint(result.exception)
        msg = 'Retry: exception' if canRetry else 'Fail: exception'
        return '❌ ' + color.Fore.MAGENTA + f'{duration} ' + color.Fore.RESET + \
            msg.ljust(msgLength)[:msgLength] + \
            color.Style.BRIGHT + color.Fore.BLUE + f'({fileId}) ' + color.Style.RESET_ALL + \
            color.Style.BRIGHT + color.Fore.RED + f'{path}' + color.Style.RESET_ALL
    else:
        # Fail with other reason
        dfTable[result.file.driveId].loc[result.i, 'status'] = 'Fail'
        dfTable[result.file.driveId].loc[result.i, 'message'] = result.message
        msg = f'Retry: {result.message}' if canRetry else f'Fail: {result.message}'
        return '⛈ ' + color.Style.BRIGHT + color.Fore.WHITE + f'{duration} ' + color.Style.RESET_ALL + \
            msg.ljust(msgLength)[:msgLength] + \
            color.Style.BRIGHT + color.Fore.BLUE + f'({fileId}) ' + color.Style.RESET_ALL + \
            color.Style.BRIGHT + color.Fore.YELLOW + f'{path}' + color.Style.RESET_ALL


def process(
    user: str, outputRoot: str, job: int,
    downloadOnly: bool, noMd5: bool, fileInfoCsv: str, includeTrashed: bool,
    sharedType: str, ignoredDrives: List[str], maxRetry: int,
):
    """The implementation. """
    client = GoogleDriveClient(user)
    print('Initializing...')
    client.initialize()
    account = client.account
    outputRoot = os.path.join(outputRoot, account.user)
    os.makedirs(outputRoot, exist_ok=True)

    cfg = Config()
    dfTable: Dict[str, pd.DataFrame] = {}
    if fileInfoCsv:
        # User use fixed file info csv path
        fileList, df = __fetchFileInfoFromCsv(
            fileInfoCsv, outputRoot, noMd5, sharedType, includeTrashed)
        driveName = df['path'][0].split(os.path.sep)[0]
        dfTable = {driveName: df}
    else:
        driveList = [('MyDrive', '')]
        driveList.extend([
            (sharedDrive.name, sharedDrive.driveId) for sharedDrive in client.sharedDrives
        ])
        dfTable: Dict[str, pd.DataFrame] = {}
        downloadList: List[FileInfo] = []
        for driveName, driveId in driveList:
            # Handle ignored drive list
            if driveName in ignoredDrives:
                print(f'Drive {driveName} is marked ignored by user.')
                continue

            if downloadOnly:
                path = os.path.join(outputRoot, driveName) + '.csv'
                if (not os.path.exists(path)) or (not os.path.isfile(path)):
                    print(f'Drive {driveName} ignored, since file info CSV does not exist.')
                    continue
                fileList, df = __fetchFileInfoFromCsv(
                    path, outputRoot, noMd5, sharedType, includeTrashed)
            else:
                fileList, folderTable = __fetchFileInfo(
                    client, driveId, driveName, includeTrashed, sharedType, cfg)
                fileList, df = __processFileInfo(
                    outputRoot, fileList, folderTable, driveName, noMd5, sharedType)
            downloadList.extend(fileList)
            dfTable[driveId] = df
    print(f'Total file to download: {len(downloadList)}')

    # Downloading
    fmt = color.Fore.YELLOW + '{desc:<10}' + color.Fore.RESET + ' | ' + \
        color.Style.BRIGHT + 'Total:{percentage: 3.0f}% ' + color.Style.NORMAL + \
        '|{bar}{r_bar}'
    progress = tqdm(
        desc='Total', total=len(downloadList), ascii=True, dynamic_ncols=True, bar_format=fmt)
    downloader = Downloader(client.authId, outputRoot, job)
    completedCount = 0
    # Retry table, map from file id to retry remain count
    retryTable: Dict[str, int] = {}
    # Submit all taskes
    futures = [
        downloader.download(
            f,
            cfg.preferExportType[f.mime] if f.exportLinks else '',
            cfg.exportMimeTable[cfg.preferExportType[f.mime]][1] if f.exportLinks else '',
            i
        ) for f, i in downloadList]
    while True:
        done, notdone = wait(futures, timeout=1, return_when=ALL_COMPLETED)
        retryList = []
        for future in done:
            result: DownloadTaskResult = future.result()
            canRetry = True
            # Retry failed
            if not result.result:
                # Download fail
                file = result.file
                if file.id in retryTable:
                    retryTable[file.id] -= 1
                    if retryTable[file.id] <= 0:
                        del retryTable[file.id]
                        canRetry = False
                else:
                    # Possible to retry
                    retryList.append((file, result.i))
                    retryTable[file.id] = maxRetry
            msg = __updateResultMessage(result, dfTable, canRetry)
            progress.write(msg)
        completedCount += len(done)
        # Append retry
        retryFutures = [
            downloader.download(
                f,
                cfg.preferExportType[f.mime] if f.exportLinks else '',
                cfg.exportMimeTable[cfg.preferExportType[f.mime]][1] if f.exportLinks else '',
                i
            ) for f, i in retryList]
        progress.total += len(retryList)
        futures = retryFutures
        futures.extend(notdone)

        # Dump df every 1000 files
        if completedCount % 1000 == 0:
            # My Drive
            if '' in dfTable:
                dfTable[''].to_csv(
                    os.path.join(outputRoot, 'MyDrive.csv'), encoding='utf-8', index=False)
            # Shared drives
            for sharedDrive in client.sharedDrives:
                if sharedDrive.driveId not in dfTable:
                    continue
                dfTable[sharedDrive.driveId].to_csv(
                    os.path.join(outputRoot, f'{sharedDrive.name}.csv'),
                    encoding='utf-8', index=False)

        progress.update(len(done))
        if len(notdone) == 0:
            progress.desc = __formatDesc('Complete', None)
            progress.refresh()
            break

        # Need reauth?
        if Downloader.RequireAuth:
            client.auth()
            downloader.resetAuthKey(client.authId)
            Downloader.RequireAuth = False

        # Show downloader worker's status
        i = 0
        for status in downloader.status.values():
            if status.complete:
                continue
            progress.desc = __formatDesc(status.title, status)
            progress.refresh()
            i += 1
            if i < downloader.maxJobs:
                time.sleep(1)
    progress.close()

    if '' in dfTable:
        dfTable[''].to_csv(os.path.join(outputRoot, 'MyDrive.csv'), encoding='utf-8', index=False)
    for sharedDrive in client.sharedDrives:
        dfTable[sharedDrive.driveId].to_csv(
            os.path.join(outputRoot, f'{sharedDrive.name}.csv'), encoding='utf-8', index=False)
    failDf = pd.concat([df.loc[df['status'] == 'Fail'] for df in dfTable.values()])
    failDf.to_csv(os.path.join(outputRoot, 'fail.csv'), index=None)

    print('Complete')
    print(f'Failed files: {len(failDf)}')
    if len(failDf) > 0:
        print(f'Record of all failed files are saved to {os.path.join(outputRoot, "fail.csv")}')
