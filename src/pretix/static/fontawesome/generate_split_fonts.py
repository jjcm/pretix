#
# This file is part of pretix (Community Edition).
#
# Copyright (C) 2014-2020 Raphael Michel and contributors
# Copyright (C) 2020-2021 rami.io GmbH and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation in version 3 of the License.
#
# ADDITIONAL TERMS APPLY: Pursuant to Section 7 of the GNU Affero General Public License, additional terms are
# applicable granting you additional permissions and placing additional restrictions on your usage of this software.
# Please refer to the pretix LICENSE file to obtain the full terms applicable to this work. If you did not receive
# this file, see <https://pretix.eu/about/en/license>.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#
"""
Split the icon font into unicode-range chunks so a page only downloads the
glyph ranges of the icons it actually renders.

Regenerate the files in fonts/split/ after upgrading the icon font:

    pip install fonttools brotli
    python generate_split_fonts.py

The matching @font-face rules live in scss/_path.scss; regenerate them here
too (the script prints them) if the ranges change.
"""
import io
import os

from fontTools import subset
from fontTools.ttLib import TTFont

BASE = os.path.dirname(__file__)
SOURCE = os.path.join(BASE, 'fonts', 'fontawesome-webfont.ttf')
OUTDIR = os.path.join(BASE, 'fonts', 'split')

# All non-icon codepoints in the font ride along with the first chunk; the
# icon glyphs are split into 64-codepoint ranges of the private use area.
EXTRA_FIRST = 'U+0020,U+00A8-00AE,U+00B4,U+00C6,U+00D8,U+2122,U+221E,U+2260'
CHUNK_SIZE = 0x40
FIRST = 0xF000
LAST = 0xF500


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rules = []
    start = FIRST
    while start <= LAST:
        end = start + CHUNK_SIZE - 1
        unicodes = f'U+{start:04X}-{end:04X}'
        subset_unicodes = unicodes if start != FIRST else f'{EXTRA_FIRST},{unicodes}'
        name = f'fontawesome-webfont-{start:04X}'
        sizes = {}
        cps = []
        for part in subset_unicodes.split(','):
            part = part.replace('U+', '')
            if '-' in part:
                a, b = part.split('-')
                cps.extend(range(int(a, 16), int(b, 16) + 1))
            else:
                cps.append(int(part, 16))
        for flavor, ext in (('woff2', 'woff2'), ('woff', 'woff')):
            font = TTFont(SOURCE)
            ss = subset.Subsetter(subset.Options(hinting=True))
            ss.populate(unicodes=cps)
            ss.subset(font)
            font.flavor = flavor
            buf = io.BytesIO()
            font.save(buf)
            data = buf.getvalue()
            with open(os.path.join(OUTDIR, f'{name}.{ext}'), 'wb') as fp:
                fp.write(data)
            sizes[ext] = len(data)
        display_range = unicodes if start != FIRST else f'{EXTRA_FIRST},{unicodes}'
        rules.append((name, display_range))
        print(f'{name}: woff2 {sizes["woff2"]}B, woff {sizes["woff"]}B, {display_range}')
        start = end + 1

    print()
    for name, display_range in rules:
        print(f"""@font-face {{
  font-family: 'FontAwesome';
  src: url(static('fontawesome/fonts/split/{name}.woff2')) format('woff2'),
    url(static('fontawesome/fonts/split/{name}.woff')) format('woff');
  font-weight: normal;
  font-style: normal;
  unicode-range: {display_range};
}}""")


if __name__ == '__main__':
    main()
