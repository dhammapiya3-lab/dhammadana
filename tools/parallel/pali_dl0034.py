import re
LOW = 'abcdefghijklmnopqrstuvwxyzāīūñṁṃṅṇṭḍḷ'
ITAL = {'5': 'ṁ', '8': 'ṇ', ';': 'ṭ', '=': 'ḷ', '>': 'ṅ'}
ITAL_UP = {'D': 'ḍ', 'H': 'ṃ'}
ROM_UP = {'S': 'ṇ', 'X': 'ḍ', 'R': 'ṭ', 'P': 'ḷ', 'L': 'ṅ'}
CAPS = {'e': 'Ṅ', 'g': 'Ṭ', 'f': 'Ḷ', 'h': 'Ṇ', 'i': 'Ḍ'}
BOLD = {';': 'ṇ', '<': 'ḍ', 'J': 'ṁ'}
def kind(f):
    if 'CC78' in f: return 'I'
    if 'CE88' in f: return 'B'
    if 'C630' in f or '3CBE5C8' in f: return 'R'
    return 'O'
def isl(c): return c.lower() in LOW and c.isalpha()
def fixline(chars):
    """chars: list of (c, font). returns fixed string"""
    out = [c for c, f in chars]; ks = [kind(f) for c, f in chars]; n = len(out)
    def L(i): return 0 <= i < n and isl(out[i])
    for i, (c, f) in enumerate(chars):
        k = ks[i]
        prev = out[i-1] if i else ' '; nxt = chars[i+1][0] if i+1 < n else ' '
        if k == 'I':
            CODE = '58;=>'
            isP = lambda ch: ch.isalpha() or ch in CODE
            if c in ITAL:
                mid = (L(i-1) or prev in CODE) and isP(nxt)
                end = (c in '58=' and L(i-1) and not isP(nxt)) or (c == '>' and L(i-1) and not ''.join(x for x, _ in chars[i+1:]).strip())
                start = (prev in ' ·(‘’-“' or i == 0) and (nxt.isalpha() and nxt.islower() or nxt in CODE and nxt != '5') and not (c in '58' and re.match(r'[a-z](:|th\b)', ''.join(x for x, _ in chars[i+1:i+4])))
                if mid or end or start: out[i] = ITAL[c]
            elif c == 'H' and i and out[i-1].isalpha() and out[i-1].islower() and not nxt.isalpha(): out[i] = 'ṃ'
            elif c == 'D' and i and (out[i-1] in 'ṇṭ' or out[i-1].islower() and out[i-1].isalpha()) and (nxt.islower() or nxt == '·'): out[i] = 'ḍ'
            elif c == 'M' and nxt == ';': out[i] = 'Ṭ'
            elif c == 'K' and i > 1 and out[i-1] == 'a' and out[i-2] == 'S' and nxt == 'g': out[i] = 'ṅ'
        elif k == 'R':
            if c in ROM_UP and i and isl(out[i-1]) and out[i-1].islower() and (nxt.islower() or nxt in ROM_UP or nxt == 'D'):
                out[i] = ROM_UP[c]
            elif c == 'D' and i and out[i-1] == 'ṇ' and nxt.islower(): out[i] = 'ḍ'
            elif c == ']' and L(i-1) and nxt.isalpha(): out[i] = 'ṁ'
            elif c == 'K' and i and out[i-1] == 'a' and nxt == 'g' and i > 1 and out[i-2] == 'S': out[i] = 'ṅ'
        elif k == 'B':
            if c in ';<' and L(i-1) and (nxt.isalpha() or nxt in ';<'): out[i] = BOLD[c]
            elif c == 'J' and L(i-1) and out[i-1].islower() and nxt.islower(): out[i] = 'ṁ'
    s = ''.join(out)
    # 모두 큰 글자 낱말 속 작은 글자 = 큰 발음 부호 글자 (AeGULIMĀLA → AṄGULIMĀLA)
    def caps(m):
        w = m.group(0)
        up = sum(1 for ch in w if ch.isupper()); lo = [ch for ch in w if ch.islower()]
        if up >= 3 and lo and all(ch in CAPS for ch in lo) and len(lo) <= 2 and (len(w) >= 6 or any(ch in 'ĀĪŪ' for ch in w)):
            return ''.join(CAPS.get(ch, ch) for ch in w)
        return w
    return re.sub(r"[A-Za-zĀĪŪÑṄṬḌṆḶṀ]{3,}", caps, s)
