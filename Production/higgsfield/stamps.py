"""Version stamps of the film's files, one per file.

Browsers keep the film's files under their address. The page adds a stamp to each address (`?v=...`), so a changed file is
fetched again at once; an unchanged file keeps its stamp, so a returning visitor's browser does not download it again.
Most files carry the page's base stamp `MV`; `FV` in Source/index.html lists the files whose stamp differs from it.

Run after changing any file in Source/v, Source/vi, Source/tiles/m, Source/tiles/im or Source/assets/tiles-worker.js:
    python3 Production/higgsfield/stamps.py
It compares every file with stamps.json (next to this script), gives each changed or new file today's next stamp
(for example 20261123-1), and writes FV. `--init STAMP` records the files as they are now under STAMP (done once)."""
import hashlib, json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..', 'Source'))
STATE = os.path.join(HERE, 'stamps.json')
PAGE = os.path.join(SRC, 'index.html')
DIRS = ['v', 'vi', 'tiles/m', 'tiles/im']
EXTRA = ['assets/tiles-worker.js']


def files():
    out = []
    for d in DIRS:
        for f in sorted(os.listdir(os.path.join(SRC, d))):
            if f.endswith(('.mp4', '.webp')): out.append(f'{d}/{f}')
    return out + EXTRA


def sha(p):
    h = hashlib.sha1()
    with open(os.path.join(SRC, p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]


def base_of_page():
    m = re.search(r'const MV = "\?v=([^"]+)";', open(PAGE, encoding='utf-8').read())
    return m.group(1)


def write_fv(state):
    fv = {p: e['v'] for p, e in sorted(state['files'].items()) if e['v'] != state['base']}
    s = open(PAGE, encoding='utf-8').read()
    new = '/*FV*/' + json.dumps(fv, separators=(',', ':')) + '/*FV*/'
    s2, n = re.subn(r'/\*FV\*/.*?/\*FV\*/', lambda m: new, s, flags=re.S)
    if n != 1: sys.exit('index.html has no /*FV*/ ... /*FV*/ block')
    if s2 != s:
        with open(PAGE, 'w', encoding='utf-8', newline='') as f: f.write(s2)
    return fv


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--init':
        stamp = sys.argv[2]
        if stamp != base_of_page(): sys.exit(f'--init needs the page\'s base stamp ({base_of_page()})')
        state = {'base': stamp, 'files': {p: {'sha': sha(p), 'v': stamp} for p in files()}}
    else:
        state = json.load(open(STATE))
        if state['base'] != base_of_page(): sys.exit('MV in index.html is not the base stamp in stamps.json')
        today = datetime.date.today().strftime('%Y%m%d')
        used = [int(e['v'].split('-')[1]) for e in state['files'].values() if e['v'].startswith(today + '-')]
        if state['base'].startswith(today + '-'): used.append(int(state['base'].split('-')[1]))
        stamp = f'{today}-{max(used, default=0) + 1}'
        now = {p: sha(p) for p in files()}
        changed = [p for p in now if p not in state['files'] or state['files'][p]['sha'] != now[p]]
        gone = [p for p in state['files'] if p not in now]
        for p in gone: del state['files'][p]
        for p in changed: state['files'][p] = {'sha': now[p], 'v': stamp}
        print(f'{len(changed)} changed or new' + (f', stamp {stamp}' if changed else '') + (f'; {len(gone)} gone' if gone else ''))
        for p in changed: print('  ', p)
    json.dump(state, open(STATE, 'w'), indent=0, sort_keys=True)
    fv = write_fv(state)
    print(f'{len(state["files"])} files, {len(fv)} with their own stamp (FV)')


if __name__ == '__main__':
    main()
