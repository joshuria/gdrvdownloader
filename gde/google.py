# -*- coding: utf-8 -*-
from typing import Dict, Generator, List
from datetime import datetime
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .file import FileInfo


class GoogleDriveClient:
    """Implementation of necessary google drive API v3 operations.

    This class only uses read operations

    # Auth Flow
    This implementation uses `InstalledAppFlow`, and user must provides `client_secrets.json` for
    performing OAuth to Google Drive API. The `client_secrets.json` can be downlooaded in GCP
    *Certificates* under *API and Service* page. The downloaded credentials must rename to
    `client_secrets.json` and put in root folder of this repo.

    For security reason, the credential file is highly recommanded not to share with others.

    # Auth Token
    The OAUTH token is saved to `tokens/<account email>.json`. The constructor of this class
    requires user's email address to identify if user must do auth again.
    """

    __Scope = [
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
    ]
    """API scope definitions."""

    class AccountInfo:
        """Defines drive account information."""
        def __init__(
            self,
            user: Dict[str, str],
            storageQuota: Dict[str, int],
            exportFormats: Dict[str, List[str]]
        ):
            self.__user = user['emailAddress']
            self.__quotaLimit = \
                int(storageQuota['limit']) if 'limit' in storageQuota else float('inf')
            self.__quotaUsage = int(storageQuota['usage'])
            self.__quotaInDrive = int(storageQuota['usageInDrive'])
            self.__quotaInTrash = int(storageQuota['usageInDriveTrash'])
            self.__exportFormats = exportFormats

        @property
        def user(self) -> str:
            """Get account email address."""
            return self.__user

        @property
        def quotaLimit(self) -> int:
            """Get quota of `My Drive` limit."""
            return self.__quotaLimit

        @property
        def totalUsage(self) -> int:
            """Get total storage usage cross all google services."""
            return self.__quotaUsage

        @property
        def usageInDrive(self) -> int:
            """Get total usage in Google Drive."""
            return self.__quotaInDrive

        @property
        def usageInTrash(self) -> int:
            """Get total usage in Google Drive trash."""
            return self.__quotaInTrash

        @property
        def exportFormats(self) -> Dict[str, List[str]]:
            """Get list of supproted exporting types."""
            return self.__exportFormats


    class SharedDriveInfo:
        """Defines shared drive information."""

        def __init__(self, id: str, name: str):
            self.__name = name
            self.__id = id

        @property
        def name(self) -> str:
            """Get name of this dirve."""
            return self.__name

        @property
        def driveId(self) -> str:
            """Get id if this drive."""
            return self.__id


    def __init__(self, userAccount: str):
        self.__authId = ''
        self.__targetUserAccount = userAccount.lower()
        self.__service = None
        self.__account = None
        self.__sharedDrives = []

    @property
    def authId(self) -> str:
        """Get OAuth certificate key for sending request to google apis.
         This field is valid after `auth()` success.
        """
        return self.__authId

    @property
    def account(self) -> AccountInfo:
        """Get drive owner's account."""
        return self.__account

    @property
    def sharedDrives(self) -> List[SharedDriveInfo]:
        """Get all shared drives of current account."""
        return self.__sharedDrives

    def initialize(self):
        """Do initialization.
        This method will do:
           - auth
           - queryAccount
           - querySharedDrives
        """
        self.auth()
        self.__account = self.queryAccount()
        self.__sharedDrives = self.querySharedDrives()

    def auth(self):
        """Do Google OAuth flow."""
        os.makedirs('tokens', exist_ok=True)

        credential = None
        tokenFilePath = f'tokens/{self.__targetUserAccount}.json'
        if os.path.exists(tokenFilePath):
            credential = Credentials.from_authorized_user_file(
                tokenFilePath, GoogleDriveClient.__Scope)

        if (credential is None) or (not credential.valid):
            if credential and credential.expired and credential.refresh_token:
                # Expired: refresh it
                credential.refresh(Request())
            else:
                # New user: open browser and ask auth
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json', GoogleDriveClient.__Scope)
                credential = flow.run_local_server(port=0)

            # Save credential'
            with open(tokenFilePath, 'w', encoding='utf-8') as file:
                file.write(credential.to_json())
        self.__authId = credential.token
        self.__service = build('drive', 'v3', credentials=credential)

    def queryAccount(self) -> AccountInfo:
        """Request `About` API and get account info. """
        # pylint: disable=no-member
        result = self.__service.about().get(
            fields='user(emailAddress), storageQuota, exportFormats'
        ).execute()
        return GoogleDriveClient.AccountInfo(**result)

    def querySharedDrives(self) -> List[SharedDriveInfo]:
        """Query all shared drives."""
        param = {'pageSize': 20, 'fields': 'nextPageToken, drives(id, name)'}
        driveList = []
        while True:
            # pylint: disable=no-member
            result = self.__service.drives().list(**param).execute()
            driveList.extend(GoogleDriveClient.SharedDriveInfo(**info) for info in result['drives'])
            if 'nextPageToken' in result:
                param['pageToken'] = result['nextPageToken']
            else:
                break
        return driveList

    def queryFiles(
        self, driveId = '', pageSize=100, trashed=False, sharedType='owned',
    ) -> Generator[List[FileInfo], None, None]:
        """Query block of files info.
        This is a generator function, a small set of files info will be returned in every call.
        Sample query flow:

        ```python
        # Query My Drive files
        fileList, pageToken = client.queryFiles()
        while pageToken:
            files, pageToken = client.queryFiles(pageToken)
            fileList.extend(files)
        ```

         :param driveId: shared drive Id. Set to empty string to query **My Drive**.
         :param pageToken: paging token for querying.
         :param pageSize: max # of file to query.
         :param trashed: include trashed file or not.
         :param sharedType: fetch files with owner filter.
            - both: include both shared with me and owned by me.
            - owned: only owned by me.
            - shared: only shared with me.
         :returns: list of FileInfo and a token for querying in next iteration.
        """
        # Query root folder id
        # Folder does not have access time (viewedByMeTime)
        if driveId:
            yield [FileInfo(driveId, '', 'application/vnd.google-apps.folder',
                datetime.utcnow(), datetime.utcnow(), datetime.utcnow(), driveId=driveId)]
        else:
            # pylint: disable=no-member
            result = self.__service.files().get(
                fileId='root', fields='id, mimeType, modifiedTime, createdTime, viewedByMeTime'
            ).execute()
            yield [FileInfo(result['id'], '', result['mimeType'],
                result['createdTime'], result['modifiedTime'], driveId=driveId)]

        param = {
            'pageSize': pageSize,
            'fields' : 'nextPageToken, ' + \
                'files(id, name, parents, mimeType, exportLinks, ' + \
                    'modifiedTime, createdTime, viewedByMeTime, size, md5Checksum, trashed, ' + \
                    'ownedByMe)'
        }
        if not trashed:
            param['q'] = 'trashed = false'
        if not driveId:
            # My Drive only, shared drives use 'me' in owners will return nothing but just root
            if sharedType == 'owned':
                if 'q' in param:
                    param['q'] += ' and \'me\' in owners'
                else:
                    param['q'] = '\'me\' in owners'
            elif sharedType == 'shared':
                if 'q' in param:
                    param['q'] += ' and (not \'me\' not in owners)'
                else:
                    param['q'] = 'not \'me\' in owners'
        if driveId:
            param['driveId'] = driveId
            param['includeItemsFromAllDrives'] = True
            param['supportsAllDrives'] = True
            param['corpora'] = 'drive'
        while True:
            # pylint: disable=no-member
            result = self.__service.files().list(**param).execute()
            yield [FileInfo(**info, driveId=driveId) for info in result['files']]
            if 'nextPageToken' in result:
                param['pageToken'] = result['nextPageToken']
            else:
                break
