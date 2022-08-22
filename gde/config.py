# -*- coding: utf-8 -*-
import json
from typing import Dict


class Config:
    """Settings for gde implementation."""

    def __init__(self, filePath: str = 'settings.json') -> None:
        try:
            with open(filePath, 'r', encoding='utf-8') as f:
                self.__config = json.load(f)
        except IOError:
            # File does not exist?
            self.__config = {
                'queryFileInfoPageSize': 1000,  # Max 1000
                'md5ChunkSize': 1024 * 1024,  # 1 MBytes
                'downloadChunkSize': 128 * 1024, # 128 KBytes
                'mimeMapping': {
                    # Google
                    'application/vnd.google-apps.document': ['Google Docs', ''],
                    'application/vnd.google-apps.drawing': ['Google Drawing', ''],
                    'application/vnd.google-apps.form': ['Google Forms', ''],
                    'application/vnd.google-apps.jam': ['Google Jamboard', ''],
                    'application/vnd.google-apps.presentation': ['Google Slides', ''],
                    'application/vnd.google-apps.script': ['Google Apps Scripts', ''],
                    'application/vnd.google-apps.script+json': ['Google Apps JSON (.json)', '.json'],
                    'application/vnd.google-apps.site': ['Google Sites', ''],
                    'application/vnd.google-apps.spreadsheet': ['Google Sheet', ''],
                    # MS
                    'application/rtf': ['Rich Test Format (.rtf)', '.rtf'],
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                        ['Microsoft Powerpoint (.pptx)', '.pptx'],
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                        ['Microsoft Excel (.xlsx)', '.xlsx'],
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        ['Microsoft Word (.docx)', '.docx'],
                    # Openoffice
                    'application/vnd.oasis.opendocument.presentation':
                        ['OpenDocument Presentation (.odp)', '.odp'],
                    'application/vnd.oasis.opendocument.spreadsheet':
                        ['OpenDocument Spreadsheet (.ods)', '.ods'],
                    'application/vnd.oasis.opendocument.text': ['OpenDocument Text (.odt)', '.odt'],
                    'application/x-vnd.oasis.opendocument.spreadsheet':
                        ['OpenDocument Spreadsheet (.ods)', '.ods'],
                    # Other
                    'application/epub+zip': ['EPUB (.epub)', '.epub'],
                    'application/pdf': ['PDF (.pdf)', '.pdf'],
                    'application/zip': ['Zip (.zip)', '.zip'],
                    'image/jpeg': ['Jpeg (.jpg)', '.jpg'],
                    'image/png': ['PNG (.png)', '.png'],
                    'image/svg+xml': ['SVG (.svg)', '.svg'],
                    'text/csv': ['Comma-Separated Values (.csv)', '.csv'],
                    'text/html': ['HTML (.html)', '.html'],
                    'text/plain': ['Plain Text (.txt)', '.txt'],
                    'text/tab-separated-values': ['Tab-Separated Values (.tsv)', '.tsv'],
                },
                'preferExportMimeType': {
                    # Docs
                    'application/vnd.google-apps.document':
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    # Sheet
                    'application/vnd.google-apps.spreadsheet':
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    # Jamboard
                    'application/vnd.google-apps.jam':
                        'application/pdf',
                    # AppScript
                    'application/vnd.google-apps.script':
                        'application/vnd.google-apps.script+json',
                    # Slides
                    'application/vnd.google-apps.presentation':
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    # Form
                    'application/vnd.google-apps.form':
                        'application/zip',
                    # Drawing
                    'application/vnd.google-apps.drawing':
                        'image/svg+xml',
                    # Site
                    'application/vnd.google-apps.site':
                        'text/plain',
                }
            }

    @property
    def queryFileInfoPageSize(self) -> int:
        """Get page size when querying file info."""
        return self.__config['queryFileInfoPageSize']

    @property
    def md5ChunkSize(self) -> int:
        """Get MD5 chunksize when computing local file hash."""
        return self.__config['md5ChunkSize']

    @property
    def downloadChunkSize(self) -> int:
        """Get download iteration chunk size."""
        return self.__config['downloadChunkSize']

    @property
    def exportMimeTable(self) -> Dict[str, str]:
        """Get export MIME type mapping to application such as PDF, Microsoft Excel."""
        return self.__config['mimeMapping']

    @property
    def preferExportType(self) -> Dict[str, str]:
        """Get user preferred exporting MIME type."""
        return self.__config['preferExportMimeType']
