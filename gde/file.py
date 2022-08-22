# -*- coding: utf-8 -*-
from cmath import isnan
from datetime import datetime
from enum import Enum
from typing import Dict, List
import hashlib
import json
import os
from dateutil.parser import parse


class FileType(Enum):
    """Defines supported file types."""
    FILE = 'File'
    """General file, include normal file and google docs."""

    FOLDER = 'Folder'
    """Directory."""

    LINK = 'Link'
    """Accelerator link to another file or folder."""


class FileInfo:
    """Defines google drive file information.

    MIME type ref: https://developers.google.com/drive/api/guides/mime-types

    Note: shared drives does not return `ownedByMe` field, so set default value to True for
    supporting download.
    """

    def __init__(self,
        # pylint: disable=redefined-builtin
        id: str, name: str, mimeType: str,
        createdTime: str, modifiedTime: str, viewedByMeTime: str = '',
        parents: List[str] = None, ownedByMe: bool = True,
        size: int = 0, md5Checksum: str = '', exportLinks: Dict[str, str] = None,
        trashed: bool = False, driveId: str = '', **kwargs
    ):
        self.__id = id
        self.__name = name
        self.__owned = ownedByMe
        self.__parents = parents if parents else []
        self.__driveId = driveId
        self.__md5 = md5Checksum
        self.__size = size
        self.__ctime = parse(createdTime) if isinstance(createdTime, str) else createdTime
        self.__mtime = parse(modifiedTime) if isinstance(modifiedTime, str) else modifiedTime
        self.__atime = parse(viewedByMeTime) \
            if isinstance(viewedByMeTime, str) and (viewedByMeTime != '') else datetime.utcnow()
        self.__mime = mimeType
        self.__exportLinks = exportLinks
        self.__trashed = trashed
        self.__path = kwargs['path'] if 'path' in kwargs else ''
        self.__type = FileType.FILE
        if mimeType == 'application/vnd.google-apps.shortcut':
            self.__type = FileType.LINK
        elif mimeType == 'application/vnd.google-apps.folder':
            self.__type = FileType.FOLDER
        # Fix type when read back from CSV
        if isinstance(self.__exportLinks, str):
            self.__exportLinks = json.loads(self.__exportLinks) if self.__exportLinks else None
        if isinstance(self.__parents, str):
            self.__parents = json.loads(self.__parents) if self.__parents else None

    @property
    def id(self) -> str:
        """Get id of this file."""
        return self.__id

    @property
    def name(self) -> str:
        """Get file name of this file."""
        return self.__name

    @property
    def owned(self) -> bool:
        """Specify this file is owned by current account."""
        return self.__owned

    @property
    def md5(self) -> str | None:
        """Get MD5 hash of this file.
        For exported files (such as google docs), this value will be empty string.
        """
        return self.__md5

    @property
    def size(self) -> int:
        """Get file size in byte.
        For exported files (such as google docs), this value will be 0.
        """
        return self.__size

    @property
    def ctime(self) -> datetime:
        """Get create time of this file."""
        return self.__ctime

    @property
    def mtime(self) -> datetime:
        """Get last modify time of this file."""
        return self.__mtime

    @property
    def atime(self) -> datetime:
        """Get last access (by me) time of this file."""
        return self.__atime

    @property
    def parents(self) -> List[str]:
        """Get list of parent folder (may not ordered)."""
        return self.__parents

    @property
    def mime(self) -> str:
        """Get mime type of this file."""
        return self.__mime

    @property
    def exportLinks(self) -> Dict[str, str] | None:
        """Get all supported export links.
         For non-exportable files, this value will be None.
        """
        return self.__exportLinks

    @property
    def trashed(self) -> bool:
        """Get if current file has been trashed."""
        return self.__trashed

    @property
    def driveId(self) -> str:
        """Get drive Id. Return empty string if drive is `My Drive`."""
        return self.__driveId

    @property
    def fileType(self) -> FileType:
        """Get file type."""
        return self.__type

    @property
    def path(self) -> str:
        """Get path in drive of this file.
         Note this field must be updated explicitly.
        """
        return self.__path

    @path.setter
    def path(self, v: str):
        """Set path."""
        self.__path = v

    def isFolder(self) -> bool:
        """Get if this file is a folder."""
        return self.fileType == FileType.FOLDER

    def asDict(self) -> Dict[str, str | int | datetime]:
        """Convert data to dict representation."""
        return {
            'id': self.id,
            'name': self.name,
            'mimeType': self.mime,
            'parents': self.parents,
            'driveId': self.driveId,
            'createdTime': self.ctime,
            'modifiedTime': self.mtime,
            'viewedByMeTime': self.atime,
            'md5Checksum': self.md5,
            'exportLinks': self.exportLinks,
            'trashed': self.trashed,
            'path': self.path,
            'type': self.fileType.value,
            'ownedByMe': self.owned,
        }

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return json.dumps(self.asDict(), indent=4, default=str)


def md5(filePath: str, chunkSize: int = 1024 * 1024 * 4) -> str:
    """Compute MD5 hash on given file.

     :param filePath: path to file to compute.
     :param chunkSize: file chunk size. Default is 4MBytes. Note that this value must be multiplier
        of **128 bytes**.
     :returns: hex formatted MD5 hash (digest).
    """
    m = hashlib.md5()
    with open(filePath, 'rb') as f:
        while True:
            data = f.read(chunkSize)
            if not data:
                break
            m.update(data)
    return m.hexdigest()


def setFileTime(filePath: str, mtime: datetime, atime: datetime) -> bool:
    """Set file modified time and access time."""
    # atime and mtime
    os.utime(filePath, (atime.timestamp(), mtime.timestamp()))
