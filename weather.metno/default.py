# -*- coding: utf-8 -*-
import os
import sys

import xbmcaddon

CWD = xbmcaddon.Addon().getAddonInfo('path')
sys.path.insert(0, os.path.join(CWD, 'resources', 'lib'))

from metno import Main  # noqa: E402

if __name__ == '__main__':
    Main(sys.argv[1] if len(sys.argv) > 1 else '1')
