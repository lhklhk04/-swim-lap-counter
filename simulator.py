# ============================================================
#  simulator.py - 실제 수영장 대신 쓰는 가상 입력 데이터 생성기
#  (1) RFID 리더 태그 기록  (2) 카메라 추적 좌표(노이즈·끊김 포함)
#  실제 설비가 생기면 이 파일만 실제 입력으로 바꾸면 된다.
# ============================================================

import numpy as np
from config import LANE_LENGTH, FPS, POS_NOISE, DROPOUT_RATE

# ---------- 데모 시나리오: 한 레인, 19시 회차 ----------
# tag: 입장 태그 시각(회차 시작 후 초), lengths: 실제 편도 수(정답),
# speed: 수영 속도(m/s), rest_every/rest: 몇 편도마다 벽에서 몇 초 쉬는지,
# stop: (몇 번째 편도, 멈춘 초) 레인 중간 정지, exit_tag: 퇴장 태그 여부
SCENARIO = [
    dict(key="103", age="성인",   member=True,  tag=20,  lengths=20, speed=1.00, rest_every=4,  rest=20),
    dict(key="215", age="어린이", member=False, tag=95,  lengths=12, speed=0.65, rest_every=2,  rest=25),
    dict(key="087", age="청소년", member=True,  tag=240, lengths=30, speed=1.30, rest_every=10, rest=30,
         stop=(13, 25)),
    dict(key="150", age="성인",   member=False, tag=600, lengths=16, speed=0.90, rest_every=4,  rest=15,
         exit_tag=False),
]
GHOST_TAGS = [("221", 1400)]   # 태그만 하고 레인에 들어오지 않은 경우(매칭 실패 예외)


def swim_path(spec, rng):
    """[시뮬레이션] 수영자 1명의 실제 위치 x(t)와 좌우 위치 y(t)를 만든다.
    입장 후 1~4초 걸어 들어와 벽(x=0)에서 출발하고, 짝수 편도를 마치면 입구 쪽 벽에서 끝난다."""
    xs, ys = [], []
    x, d = 0.0, 1                                   # d = +1(정방향) / -1(역방향)
    stop_len, stop_sec = spec.get("stop", (None, 0))
    for i in range(1, spec["lengths"] + 1):
        v = spec["speed"] * rng.uniform(0.92, 1.08)  # 편도마다 속도가 조금씩 다름
        n = int(LANE_LENGTH / v * FPS)
        seg = np.linspace(0, LANE_LENGTH, n) if d == 1 else np.linspace(LANE_LENGTH, 0, n)
        if i == stop_len:                           # 레인 한가운데서 멈춤(안전 알림 대상)
            mid = n // 2
            seg = np.concatenate([seg[:mid], np.full(stop_sec * FPS, seg[mid]), seg[mid:]])
        xs.extend(seg)
        ys.extend([0.55 * d] * len(seg))            # 순환 수영: 갈 때 오른쪽, 올 때 왼쪽
        pause = int(rng.uniform(2, 4) * FPS)        # 턴할 때 벽에서 잠깐 머무름
        if i % spec["rest_every"] == 0 and i != spec["lengths"]:
            pause += spec["rest"] * FPS             # 정해진 간격마다 벽에서 휴식
        xs.extend([seg[-1]] * pause)
        ys.extend([0.0] * pause)
        d *= -1
    return np.array(xs), np.array(ys)


def build_scenario(seed=7):
    """[시뮬레이션] 시나리오 전체를 만들어 (태그 기록, 카메라 트랙, 정답) 세 가지를 반환한다."""
    rng = np.random.default_rng(seed)
    tags, tracks, truth = [], [], {}
    for spec in SCENARIO:
        x, y = swim_path(spec, rng)
        appear = spec["tag"] + rng.uniform(1.0, 4.0)          # 태그 후 1~4초 뒤 카메라에 등장
        t = appear + np.arange(len(x)) / FPS
        tags.append((round(spec["tag"], 1), spec["key"]))      # 입장 태그
        if spec.get("exit_tag", True):
            tags.append((round(t[-1] + 3.0, 1), spec["key"]))  # 물에서 나와 3초 뒤 퇴장 태그
        obs = x + rng.normal(0, POS_NOISE, len(x))             # 카메라 위치 오차
        obs[rng.random(len(x)) < DROPOUT_RATE] = np.nan        # 추적이 끊긴 프레임
        tracks.append({"t": t, "x": np.clip(obs, -0.5, LANE_LENGTH + 0.5), "y": y})
        truth[spec["key"]] = spec
    for key, tt in GHOST_TAGS:
        tags.append((tt, key))
    tracks.sort(key=lambda tr: tr["t"][0])                     # 등장 순서대로 트랙 번호 부여
    for i, tr in enumerate(tracks, 1):
        tr["id"] = i
    tags.sort()
    return tags, tracks, truth
