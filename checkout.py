# ============================================================
#  checkout.py - 세션 종료와 정산서 출력 (과제 4 정산 기능 연결)
# ============================================================

from config import BASIC_FEE, MEMBER_DISCOUNT, SESSION_START, SESSION_MINUTES, STOP_SECONDS


def clock(sec, start=SESSION_START):
    """[출력 보조] 회차 시작 후 경과 초를 'HH:MM:SS' 시각 문자열로 바꾼다."""
    h, m = map(int, start.split(":"))
    total = h * 3600 + m * 60 + int(sec)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def to_mmss(seconds):
    """[출력 보조] 초를 'M분 SS초' 문자열로 바꾼다. (과제 4 재사용)"""
    seconds = int(round(seconds))
    return f"{seconds // 60}분 {seconds % 60:02d}초"


def calc_entry_fee(age, is_member):
    """[요금] 연령 구분과 회원 여부로 (기본요금, 할인액, 결제금액)을 계산한다. (과제 4 재사용)"""
    fee = BASIC_FEE[age]
    discount = int(fee * MEMBER_DISCOUNT) if is_member else 0
    return fee, discount, fee - discount


def close_open_sessions(sessions, end=SESSION_MINUTES * 60):
    """[세션 관리] 회차가 끝나는 50분에 아직 열려 있는(퇴장 태그를 안 한) 세션을 모두 종료한다.
    종료 시각은 50분이 아니라 카메라에 마지막으로 보인 시각으로 저장한다. 종료한 키 목록을 반환한다."""
    closed = []
    for s in sessions.values():
        if s["status"] == "수영 중":
            s["exit"] = float(s["track"]["t"][-1])
            s["status"] = "50분 일괄 종료"
            closed.append(s["key"])
    return closed


def print_receipt(session, spec, record, alerts):
    """[출력] 키 하나의 이용 정산서(요금 + 오늘의 운동 기록 + 안전 알림)를 출력한다."""
    fee, discount, total = calc_entry_fee(spec["age"], spec["member"])
    used = (session["exit"] - session["enter"]) / 60
    line = "=" * 42
    print(line)
    print(f"  자유수영 이용 정산서  (락커키 {session['key']}번)")
    print(line)
    print(f"  이용 구분 : {spec['age']} {'회원' if spec['member'] else '비회원'}")
    print(f"  이용 시간 : {clock(session['enter'])} ~ {clock(session['exit'])} ({used:.0f}분)")
    print(f"  종료 방식 : {session['status']}")
    print("-" * 42)
    print(f"  기본 요금 : {fee:>8,}원")
    print(f"  회원 할인 : {-discount:>8,}원")
    print(f"  결제 금액 : {total:>8,}원")
    print("-" * 42)
    print("  [오늘의 운동 기록]")
    print(f"  편도 횟수 : {record['count']}회   총 거리 : {record['distance']}m")
    if record["count"]:
        print(f"  평균 편도 : {to_mmss(record['avg'])}   최고 편도 : {to_mmss(record['best'])}")
    for t, pos in alerts:
        print(f"  ! 안전 알림 {clock(t)} - 레인 {pos:.0f}m 지점에서 {STOP_SECONDS}초 이상 정지")
    print(line)
    return total
