# -*- coding: utf-8 -*-
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import current_thread
from typing import Dict
import hashlib
import os
import time
import random
import requests
from .file import FileInfo, setFileTime


class _TaskStatus:
    """Download status of each task."""

    def __init__(self) -> None:
        self.__title = ''
        self.__total = 0
        self.__current = 0
        self.__complete = False
        self.__message = ''

    @property
    def title(self) -> str:
        """Get title of this download task."""
        return self.__title

    @property
    def total(self) -> int:
        """Get total bytes of current task."""
        return self.__total

    @property
    def current(self) -> int:
        """Get downloaded bytes."""
        return self.__current

    @property
    def complete(self) -> bool:
        """Get if this task has completed."""
        return self.__complete

    @property
    def message(self) -> str:
        """Get extra message."""
        return self.__message

    def setMessage(self, msg: str):
        """Set message."""
        self.__message = msg

    def setTask(self, title: str, total: int):
        """Set new task."""
        self.__title = title
        self.__total = total
        self.__current = 0
        self.__complete = False
        self.__message = ''

    def update(self, v: int):
        """Update current value."""
        self.__current += v

    def setComplete(self):
        """Mark current status is complete."""
        self.__complete = True


class DownloadTaskResult:
    """Defines result of a download task."""

    def __init__(
        self, fileInfo: FileInfo, result: bool, msg: str, i: int, md5: str,
        e: Exception,
        requestTime: timedelta, downloadTime: timedelta,
    ) -> None:
        self.__file = fileInfo
        self.__result = result
        self.__msg = msg
        self.__i = i
        self.__md5 = md5
        self.__e = e
        self.__requestTime = requestTime
        self.__downloadTime = downloadTime

    @property
    def file(self) -> FileInfo:
        """Get file info instance."""
        return self.__file

    @property
    def result(self) -> bool:
        """Get task is success or fail."""
        return self.__result

    @property
    def message(self) -> str:
        """Get extra message."""
        return self.__msg

    @property
    def i(self) -> int:
        """Get index to all file list."""
        return self.__i

    @property
    def md5(self) -> str:
        """Get MD5 of downloaded file."""
        return self.__md5

    @property
    def exception(self) -> Exception | None:
        """Get exception during task running."""
        return self.__e

    @property
    def requestTime(self) -> timedelta:
        """Get requesting to Google API time."""
        return self.__requestTime

    @property
    def downloadTime(self) -> timedelta:
        """Get total download time. """
        return self.__downloadTime


class Downloader:
    """Perform downloading by given google OAuth key and url."""

    RequireAuth = False
    """Require to re-auth."""

    def __init__(self, authKey: str, outputRootPath: str, maxTask: int = 8) -> None:
        self.__authKey = authKey
        self.__status = {}
        self.__outputRootPath = outputRootPath
        self.__maxJobs = maxTask
        self.__pool = ThreadPoolExecutor(max_workers=maxTask, thread_name_prefix='DW')

    @property
    def status(self) -> Dict[int, _TaskStatus]:
        """Get all downloading status.
        Map from thread/process id to status instance.
        """
        return self.__status

    @property
    def maxJobs(self) -> int:
        """Get max concurrent jobs."""
        return self.__maxJobs

    def resetAuthKey(self, authKey: str):
        """Reset OAuth key."""
        self.__authKey = authKey

    def download(
        self, file: FileInfo, useExportMime: str = '', fileExt: str = '', i: int = 0
    ) -> Future[DownloadTaskResult]:
        """Download file with GET request and set jwt key.
        This method can also do MD5 check if md5 is provided.

         :param file: google drive file info.
         :param useExportMime: use this MIME type when file requres export.
         :param fileExt: file extension to append when exporting file.
         :param i: index of given file in all file list. This is for fast update download result
            back to csv.
        """
        fullPath = os.path.join(self.__outputRootPath, file.path)
        os.makedirs(os.path.dirname(fullPath), exist_ok=True)
        return self.__pool.submit(self.__downloadImpl, file, useExportMime, fileExt, i)

    def __downloadImpl(
        self, file: FileInfo, useExportMime: str, fileExt: str, i: int
    ) -> DownloadTaskResult:
        """Implementation of downloading.
        This method can also do MD5 check if md5 is provided.
        """
        thread = current_thread()
        if thread.ident not in self.status:
            self.status[thread.ident] = _TaskStatus()
        status = self.status[thread.ident]
        status.setTask(file.name, 0)

        url = f'https://www.googleapis.com/drive/v3/files/{file.id}?alt=media' \
            if not file.exportLinks else file.exportLinks[useExportMime]

        # Request download, max retry 5 times
        for retry in range(5):
            startTime = datetime.now()
            # Wait if require auth
            self.__waitAuth()
            try:
                status.setMessage('')
                resp = requests.get(
                    url=url,
                    headers={
                        'Authorization': 'Bearer ' + self.__authKey,
                        'Accept-Encoding': 'gzip, deflate',
                        'User-Agent': 'GDriveDownloader (gzip)',
                    },
                    stream=True)
                if resp.status_code == 401:
                    # need reauth
                    status.setMessage('Wait ReAuth')
                    Downloader.RequireAuth = True
                    print(f'(Retry {retry}) {file.name} need reauth: {resp.text}')
                    self.__waitAuth()
                    continue
                elif resp.status_code == 429:
                    # rate limiter
                    status.setMessage('Wait RateLimiter')
                    print(f'(Retry {retry}) {file.name} rate limiter: {resp.text}')
                    time.sleep(120)
                    continue
                    # TODO: add status message to hint waiting rate limiter, or just exit
                elif resp.status_code != 200:
                    # unknown error
                    try:
                        msg = resp.json()['error']['message']
                    except (requests.exceptions.JSONDecodeError, KeyError):
                        msg = resp.text
                    return DownloadTaskResult(
                        file, False, f'Request file fail: {msg}',
                        i, '', None, timedelta(), timedelta())
                totalSize = int(resp.headers.get('content-length', file.size))
                status.setTask(file.name, totalSize)
                requestTime = datetime.now()
            except Exception as e:
                status.setComplete()
                return DownloadTaskResult(
                    file, False, 'Request unexpected exception', i, '', e, timedelta(), timedelta())

        path = self.__getSafeFileName(os.path.join(self.__outputRootPath, file.path))
        if useExportMime and (not path.endswith(fileExt)):
            path += fileExt
        try:
            # Download & computer MD5
            h = hashlib.md5()
            with open(path, 'wb') as f:
                f.truncate(totalSize)
                for data in resp.iter_content(8192):
                    size = f.write(data)
                    status.update(size)
                    h.update(data)
            downloadTime = datetime.now()
        except Exception as e:
            status.setComplete()
            return DownloadTaskResult(
                file, False, 'Download unexpected exception', i, '', e,
                requestTime - startTime, timedelta())

        # Check MD5
        md5 = h.hexdigest()
        status.setComplete()
        if file.md5 and (md5 != file.md5):
            return DownloadTaskResult(
                file, False, 'MD5 not match', i, md5, None,
                requestTime - startTime, downloadTime - requestTime)
        setFileTime(path, file.mtime, file.atime)
        return DownloadTaskResult(
            file, True, '', i, md5, None,
            requestTime - startTime, downloadTime - requestTime)

    def __waitAuth(self, maxWaitTime: float = 3600):
        """Wait for reauth."""
        now = datetime.now()
        while Downloader.RequireAuth:
            time.sleep(2)
            if (datetime.now() - now).seconds > maxWaitTime:
                break

    def __getSafeFileName(self, path: str) -> str:
        """Get safe file name that does not duplicate with exist files."""
        if not os.path.exists(path):
            return path
        name, ext = os.path.splitext(path)
        for i in range(10):
            path = f'{name}-{i}{ext}'
            if not os.path.exists(path):
                return path
        return f'{name}-{random.randint(10, 100000)}{ext}'
