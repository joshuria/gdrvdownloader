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

        2 approaches are implemented:
          - selenium: emulate user action on browser to download.
          - gde: download through Google Drive API v3.

        For selenium approach, the following browsers are supported:
          - Chrome, chromium, edge, or other chromium related.
          - Firefox
        Note that this implementation is NOT stable and maybe failed on web page compressing flow.

        For gde approach, user is required to create personal `client_secrets.json` on GCP to enable
        Google Drive API. Please refer to our github readme for help.
        """)
    parser.add_argument(
        '--engine', '-e', choices=['selenium', 'gde'], required=True,
        help='Download by selenium or Google Drive API v3.')
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
