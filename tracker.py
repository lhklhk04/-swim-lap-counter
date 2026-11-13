# ============================================================
#  tracker.py - 락커키와 수영자(트랙)를 연결하고 좌표를 다듬는 모듈
# ============================================================

import numpy as np
from config import MATCH_WINDOW, SMOOTH_WIN


def match_track(tag_time, tracks, used_ids, window=MATCH_WINDOW):
    """[매칭] 태그 시각 이후 window초 안에 처음 나타난, 아직 아무 키와도 연결되지 않은 트랙을 찾는다.
    조건을 만족하는 트랙이 없으면 None을 반환한다(관리자 확인 대상)."""
    candidates = [tr for tr in tracks
                  if tr["id"] not in used_ids and 0 <= tr["t"][0] - tag_time <= window]
    if not candidates:
        return None
    return min(candidates, key=lambda tr: tr["t"][0])   # 가장 먼저 등장한 트랙 선택


def clean_positions(x, win=SMOOTH_WIN):
    """[전처리] 끊긴 프레임(NaN)을 앞뒤 값으로 선형 보간한 뒤, 이동평균으로 흔들림을 줄인다."""
    x = np.asarray(x, dtype=float).copy()
    idx = np.arange(len(x))
    ok = ~np.isnan(x)
    x = np.interp(idx, idx[ok], x[ok])                   # 1) 선형 보간
    pad = win // 2
    padded = np.pad(x, pad, mode="edge")                 # 양 끝이 0으로 끌려가지 않도록 가장자리 복제
    return np.convolve(padded, np.ones(win) / win, mode="valid")   # 2) 이동평균


def process_tags(tags, tracks):
    """[세션 관리] 태그 기록을 시간순으로 처리한다.
    열린 세션이 없는 키의 태그 = 입장(트랙 매칭), 열린 세션이 있는 키의 태그 = 퇴장(세션 종료).
    (세션 딕셔너리, 로그 리스트)를 반환한다."""
    sessions, log, used = {}, [], set()
    for t, key in tags:
        s = sessions.get(key)
        if s and s["status"] == "수영 중":                     # 퇴장 태그
            s["exit"], s["status"] = t, "퇴장 태그"
            log.append((t, f"퇴장 태그  Key {key} -> 세션 종료, 기록 저장"))
            continue
        tr = match_track(t, tracks, used)                      # 입장 태그
        if tr is None:
            sessions[key] = {"key": key, "track": None, "enter": t, "status": "매칭 실패"}
            log.append((t, f"입장 태그  Key {key} -> {MATCH_WINDOW:.0f}초 안에 들어온 사람 없음, 관리자 확인"))
            continue
        used.add(tr["id"])
        sessions[key] = {"key": key, "track": tr, "enter": t, "status": "수영 중"}
        log.append((t, f"입장 태그  Key {key} -> 트랙 #{tr['id']} 매칭 ({tr['t'][0] - t:.1f}초 뒤 등장)"))
    return sessions, log
