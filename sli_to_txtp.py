#!/usr/bin/env python3
"""
Convert .sli (Sound Loop Information) files to .txtp format for vgmstream.

SLI files describe loop links: when playback reaches sample `From`, jump to `To`.
In TXTP terms: loop_end = From, loop_start = To.

Usage:
    python sli_to_txtp.py bgm04.ogg.sli
    python sli_to_txtp.py *.sli
    python sli_to_txtp.py bgm04.ogg.sli --output-dir ./txtp
"""

import argparse
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# SLI parsing
# ---------------------------------------------------------------------------

def parse_sli(text: str) -> dict:
    """
    Parse an SLI file and return a dict with:
        version   : '1' or '2'
        links     : list of link dicts
        labels    : list of label dicts  (v2 only)
    """
    links = []
    labels = []

    text = text.strip()

    if not text.startswith('#'):
        # ---- Old / v1 format ----
        # Contains: LoopLength=<n>  LoopStart=<n>
        m_start  = re.search(r'LoopStart=(\d+)',  text)
        m_length = re.search(r'LoopLength=(\d+)', text)
        if not m_start or not m_length:
            raise ValueError("Unrecognised SLI v1 format (missing LoopStart/LoopLength)")
        start  = int(m_start.group(1))
        length = int(m_length.group(1))
        links.append({
            'from':      start + length,
            'to':        start,
            'smooth':    False,
            'condition': 'no',
            'ref_value': 0,
            'cond_var':  0,
        })
        return {'version': '1', 'links': links, 'labels': labels}

    # ---- v2 format ----
    # First line must be "#2.00" (or compatible)
    first_line = text.splitlines()[0]
    if not re.match(r'^#2\.\d+', first_line):
        raise ValueError(f"Unsupported SLI version header: {first_line!r}")

    def parse_block(block_text: str) -> dict:
        """Parse the inside of a { ... } block into a plain dict."""
        result = {}
        for item in re.split(r';', block_text):
            item = item.strip()
            if not item:
                continue
            m = re.match(r'(\w+)\s*=\s*(.*)', item)
            if m:
                result[m.group(1).lower()] = m.group(2).strip().strip("'\"")
        return result

    # Strip comment lines (lines starting with #)
    body_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        body_lines.append(line)
    body = ' '.join(body_lines)

    # Extract Link { ... } and Label { ... } blocks
    for m in re.finditer(r'(Link|Label)\s*\{([^}]*)\}', body, re.IGNORECASE):
        kind  = m.group(1).lower()
        block = parse_block(m.group(2))

        if kind == 'link':
            links.append({
                'from':      int(block.get('from', 0)),
                'to':        int(block.get('to', 0)),
                'smooth':    block.get('smooth', 'false').lower() == 'true',
                'condition': block.get('condition', 'no').lower(),
                'ref_value': int(block.get('refvalue', 0)),
                'cond_var':  int(block.get('condvar', 0)),
            })
        elif kind == 'label':
            labels.append({
                'position': int(block.get('position', 0)),
                'name':     block.get('name', ''),
            })

    return {'version': '2', 'links': links, 'labels': labels}


# ---------------------------------------------------------------------------
# TXTP generation
# ---------------------------------------------------------------------------

def sli_to_txtp(audio_ref: str, sli_data: dict) -> str:
    """
    audio_ref is the string that will appear inside the .txtp — either a bare
    filename or a relative path, already computed by the caller.
    """
    """
    Build TXTP content for the given audio reference and parsed SLI data.

    Strategy:
      - Unconditional links (condition=no, cond_var=0) → #I loop_start loop_end
      - A single simple loop → inline command on the filename
      - Multiple / conditional links → comments explaining what was found,
        with best-effort TXTP for the primary (first unconditional) link.
    """
    links  = sli_data['links']
    labels = sli_data['labels']

    lines = [f"# Converted from SLI (v{sli_data['version']})"]

    if not links:
        lines.append(f"# WARNING: no loop links found in SLI")
        lines.append(audio_ref)
        return '\n'.join(lines) + '\n'

    # Separate unconditional from conditional links
    unconditional = [l for l in links if l['condition'] == 'no']
    conditional   = [l for l in links if l['condition'] != 'no']

    if conditional:
        lines.append(
            f"# NOTE: {len(conditional)} conditional link(s) found "
            f"(condition-based branching is not representable in plain TXTP)."
        )
        for lk in conditional:
            lines.append(
                f"#   Skipped conditional link: From={lk['from']} To={lk['to']} "
                f"Condition={lk['condition']} RefValue={lk['ref_value']} CondVar={lk['cond_var']}"
            )

    if not unconditional:
        lines.append("# No unconditional links; outputting bare filename.")
        lines.append(audio_ref)
        return '\n'.join(lines) + '\n'

    if len(unconditional) > 1:
        lines.append(
            f"# NOTE: {len(unconditional)} unconditional links found; "
            f"using the first one. Others are listed as comments."
        )
        for lk in unconditional[1:]:
            lines.append(f"#   Extra link: From={lk['from']} To={lk['to']}")

    primary = unconditional[0]
    loop_start = primary['to']    # jump destination  → TXTP loop start
    loop_end   = primary['from']  # trigger position  → TXTP loop end

    # Build the #I command
    # #I <loop_start> [loop_end]   (both in samples)
    loop_cmd = f"#I {loop_start} {loop_end}"

    if primary['smooth']:
        lines.append("# NOTE: Smooth crossfade on this link is not representable in TXTP.")

    # Emit audio line with inline loop install
    lines.append(f"{audio_ref} {loop_cmd}")

    # Labels: any that start with ':' are flag-expression labels (engine-specific),
    # the rest are informational.
    if labels:
        lines.append("")
        lines.append("# Labels from SLI (informational only, not used by vgmstream TXTP):")
        for lb in labels:
            lines.append(f"#   Position={lb['position']} Name={lb['name']!r}")

    lines.append("")
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def audio_name_from_sli(sli_path: Path) -> str:
    """
    Derive the audio filename from the .sli path.

    bgm04.ogg.sli  →  bgm04.ogg
    bgm04.sli      →  bgm04          (bare, no audio extension known)
    """
    name = sli_path.name
    if name.lower().endswith('.sli'):
        return name[:-4]   # strip trailing .sli
    return name


def txtp_path_for(sli_path: Path, output_dir: Path | None) -> Path:
    """
    Determine where to write the .txtp file.

    bgm04.ogg.sli  →  bgm04.ogg.txtp   (same dir, or output_dir)
    """
    audio = audio_name_from_sli(sli_path)
    txtp_name = audio + '.txtp'
    base = output_dir if output_dir else sli_path.parent
    return base / txtp_name


def convert_file(sli_path: Path, output_dir: Path | None, verbose: bool) -> bool:
    """Convert one .sli file. Returns True on success."""
    try:
        raw = sli_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        print(f"ERROR reading {sli_path}: {e}", file=sys.stderr)
        return False

    try:
        sli_data = parse_sli(raw)
    except ValueError as e:
        print(f"ERROR parsing {sli_path}: {e}", file=sys.stderr)
        return False

    audio_name = audio_name_from_sli(sli_path)
    out_path   = txtp_path_for(sli_path, output_dir)

    if output_dir:
        # The .txtp will live in output_dir; the audio file sits next to the
        # original .sli.  Express the path from .txtp → audio as a relative
        # POSIX path so vgmstream can find it regardless of working directory.
        audio_abs = (sli_path.parent / audio_name).resolve()
        txtp_dir  = out_path.parent.resolve()
        audio_ref = Path(os.path.relpath(audio_abs, txtp_dir)).as_posix()
    else:
        # .txtp sits next to the audio file; bare filename is sufficient.
        audio_ref = audio_name

    txtp_content = sli_to_txtp(audio_ref, sli_data)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        out_path.write_text(txtp_content, encoding='utf-8')
    except OSError as e:
        print(f"ERROR writing {out_path}: {e}", file=sys.stderr)
        return False

    if verbose:
        print(f"  {sli_path.name}  →  {out_path}")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert .sli loop files to vgmstream .txtp format."
    )
    parser.add_argument(
        'sli_files', nargs='+', metavar='FILE.sli',
        help="One or more .sli files to convert."
    )
    parser.add_argument(
        '--output-dir', '-o', metavar='DIR', default=None,
        help="Directory for .txtp output (default: same dir as each .sli)."
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help="Suppress per-file progress output."
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    verbose    = not args.quiet
    ok = fail = 0

    for pattern in args.sli_files:
        # Support glob patterns passed as strings (useful on Windows)
        paths = list(Path('.').glob(pattern)) if '*' in pattern or '?' in pattern \
                else [Path(pattern)]
        if not paths:
            print(f"WARNING: no files matched: {pattern!r}", file=sys.stderr)
            continue
        for p in sorted(paths):
            if convert_file(p, output_dir, verbose):
                ok += 1
            else:
                fail += 1

    total = ok + fail
    if total > 1 or fail:
        status = f"Done: {ok}/{total} converted"
        if fail:
            status += f", {fail} failed"
        print(status)

    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
