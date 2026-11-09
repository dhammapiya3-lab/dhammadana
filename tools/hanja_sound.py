#!/usr/bin/env python3
"""한자 → 한글 소리 (오디오북 원고용). 표준 입력: JSON 목록 ["中部", …] → 표준 출력: {"中部": "중부", …}
- hanja 꾸러미(pip install hanja)의 낱말 사전으로 읽고, 틀리기 쉬운 불교 낱말은 아래 FIX 로 바로잡음.
"""
import sys, json, unicodedata, hanja
CHAR = {'諦': '제', '律': '율'}  # 불교 글에서 읽는 소리 (四聖諦 → 사성제)
FIX = {'一切': '일체', '說一切有部': '설일체유부', '般若': '반야', '菩提': '보리', '涅槃': '열반', '比丘': '비구', '布施': '보시', '佛': '불', '布薩': '포살', '提婆達多': '제바달다', '阿羅漢': '아라한', '阿含': '아함', '南無': '나무', '道場': '도량', '十方': '시방', '初八日': '초파일', '菩薩': '보살', '娑婆': '사바', '曼陀羅': '만다라', '六六經': '육육경'}
def say(w0):
    w = unicodedata.normalize('NFKC', w0)  # 호환 한자(念 六 不 切 등 모양만 같은 글자)를 보통 한자로
    if w in FIX: return FIX[w]
    out = hanja.translate(w, 'substitution')
    if len(out) == len(w): out = ''.join(CHAR.get(c, o) for c, o in zip(w, out))
    for k, v in sorted(FIX.items(), key=lambda x: -len(x[0])):
        if k in w: out = out.replace(hanja.translate(k, 'substitution'), v)
    return out
print(json.dumps({w: say(w) for w in json.load(sys.stdin)}, ensure_ascii=False))
