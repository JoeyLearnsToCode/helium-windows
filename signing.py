#!/usr/bin/env python3
# Copyright 2026 The Helium Authors
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
"""Package Windows release binaries without signing them."""

import argparse
import os
from pathlib import Path
import shutil

import package

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'build/src'


def emit(name, value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f'{name}={value}\n')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-outputs', type=Path, default=SOURCE / 'out/Default')
    parser.add_argument('--arch', choices=('x64', 'arm64'))
    parser.add_argument('--seven-zip', type=Path,
                        default=Path(shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'))
    args = parser.parse_args()
    args.build_outputs = args.build_outputs.resolve()
    args.seven_zip = args.seven_zip.resolve()
    return args


def main():
    args = parse_args()
    work = package.stage_build(args.build_outputs, args.seven_zip, args.arch)

    # Snapshot the staged inputs before packaging so verification can detect changes.
    expected = {'payload': package.inventory(work / 'payload'),
                'portable': package.inventory(work / 'portable'),
                'setup': package.digest(work / 'setup.exe')}

    nsis, mini, portable = package.build_packages(work, args.build_outputs, args.seven_zip)
    package.verify_packages(work, args.seven_zip, nsis, mini, portable, expected)
    emit('artifacts', work / 'artifacts')


if __name__ == '__main__':
    main()
