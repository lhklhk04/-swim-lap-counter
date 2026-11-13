# ============================================================
#  lap_counter.py - 턴 감지, 안전 알림, 운동 기록 분석
# ============================================================

import numpy as np
from config import LANE_LENGTH, FPS, WALL_ZONE, STOP_SECONDS, STOP_RANGE


def count_turns(times, x, lane=LANE_LENGTH, wall=WALL_ZONE):
    """[턴 감지] '마지막으로 도착한 벽'을 상태로 기억하고,
    반대편 벽 구간(wall m 이내)에 들어올 때만 편도 1회로 센다. 턴 시각 리스트를 반환한다.
    벽에서 쉬거나 위치가 흔들려도 같은 벽에서는 다시 세지 않는다(히스테리시스)."""
    turn_times = []
    last_wall = "start" if x[0] < lane / 2 else "end"
    for t, p in zip(times, x):
        if last_wall == "start" and p > lane - wall:
            last_wall = "end"
            turn_times.append(t)
        elif last_wall == "end" and p < wall:
            last_wall = "start"
            turn_times.append(t)
    return turn_times


def naive_count(x):
    """[비교용] 이동 방향(+/-)이 바뀔 때마다 세는 단순한 방식. 노이즈에 매우 약하다."""
    v = np.diff(np.nan_to_num(x, nan=0.0))
    sign = np.sign(v)
    sign = sign[sign != 0]
    return int(np.sum(sign[1:] != sign[:-1]))


def detect_stops(times, x, lane=LANE_LENGTH, wall=WALL_ZONE,
                 seconds=STOP_SECONDS, move=STOP_RANGE):
    """[안전 알림] 벽 구간 밖에서 seconds초 동안 이동 범위가 move m 미만이면 알림 시각을 기록한다.
    한 번 알림을 낸 뒤에는 seconds초 동안 같은 알림을 반복하지 않는다."""
    w = int(seconds * FPS)
    alerts, i = [], w
    while i <= len(x):
        seg = x[i - w:i]
        in_middle = np.all((seg > wall) & (seg < lane - wall))
        if in_middle and seg.max() - seg.min() < move:
            alerts.append((times[i - 1], float(np.mean(seg))))
            i += w
        else:
            i += 1
    return alerts


def analyze_laps(wall_times, start_time, lane=LANE_LENGTH):
    """[기록 분석] 벽 도착 시각으로 편도별 기록을 구해 (편도 수, 거리, 평균, 최고) 딕셔너리를 반환한다.
    (과제 4의 analyze_laps를 재사용, 출발 시각을 매개변수로 받도록 확장)"""
    if not wall_times:
        return {"count": 0, "distance": 0, "avg": 0, "best": 0, "splits": []}
    splits, prev = [], start_time
    for t in wall_times:
        splits.append(t - prev)             # 벽 사이 간격 = 편도 1회 기록(휴식 포함)
        prev = t
    return {"count": len(splits), "distance": int(len(splits) * lane),
            "avg": sum(splits) / len(splits), "best": min(splits), "splits": splits}
