# -*- coding: utf-8 -*-
import argparse
import os
from gde.gde import process


def createParser() -> argparse.ArgumentParser:
    """Create argparse instance."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=
        """
        gdexporter: Google Drive Exporter.

        The following functions are supported:
          - Export all drives, include My Drive and Shared Drives.
          - Export files in Share With Me.
          - Export files in trash.
          - Check downloaded file with MD5 hash.
          - Set file modified time and access time align to files on Google Drive.
          - Output file information summary into CSV.
          - Concurrent download files.

        Requirement: user is required to create personal `client_secrets.json` on GCP to enable
        Google Drive API. Please refer to our github readme for help.
        """)
    parser.add_argument(
        '--output', '-o', type=str, default='output',
        help='Path to downloaded files output root folder. Default is `./output`.')
    parser.add_argument(
        '--user', '-u', type=str, required=True,
        help='Google drive user account email.')

    grp = parser.add_argument_group('Google Drive API (gde) options')
    grp.add_argument(
        '--downloadOnly', action='store_true', required=False,
        help='Skip fetch file list, only do download based on previous stored file list CSV.')
    grp.add_argument(
        '--fileInfoCsv', '-f', type=str, required=False,
        help='Customized file info CSV path. Define this field also enable --downloadOnly and ' + \
            'disable --includeOwned, --includeShared')
    grp.add_argument(
        '--ignoreDrive', nargs='+', required=False, default=[],
        help='Drive to be ignored. Set `MyDrive` to ignore main drive.')
    grp.add_argument(
        '--includeTrashed', action='store_true', required=False, default=False,
        help='Include trashed files. Default is false.')
    grp.add_argument(
        '--job', '-j', type=int, required=False, default=8,
        help='Max concurrent download job. Default is 8.')
    grp.add_argument(
        '--noMd5', action='store_true', required=False,
        help='Skip MD5 checking.')
    grp.add_argument(
        '--sharedType', choices=['both', 'shared', 'owned'], required=False, default='owned',
        help='Export include files sharing type: shared with me, owned by me, or both.')

    return parser


if __name__ == '__main__':
    parser = createParser()
    args = parser.parse_args()
    if args.fileInfoCsv:
        args.downloadOnly = True
        args.fileInfoCsv = os.path.join(args.output, args.user, args.fileInfoCsv)

    process(
        args.user,
        args.output,
        args.job,
        args.downloadOnly,
        args.noMd5,
        args.fileInfoCsv,
        args.includeTrashed,
        args.sharedType,
        args.ignoreDrive)
