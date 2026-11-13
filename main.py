# ============================================================
#  락커키 기반 자유수영 랩 자동 카운팅 시스템 - 데모 실행 파일
#
#  실행 방법
#    python main.py               : 터미널 데모 (로그 + 정산서 + 정확도 + results 폴더 저장)
#    python main.py --animate     : 터미널 데모 후 레인 애니메이션 창 실행
#    python main.py --animate --speed 40   : 애니메이션 배속 변경
#    python main.py --gif         : 애니메이션을 results/demo.gif 로 저장
#  필요 라이브러리: numpy, matplotlib  (pip install numpy matplotlib)
# ============================================================

import argparse
import csv
import os

from config import SESSION_MINUTES
from simulator import build_scenario
from tracker import process_tags, clean_positions
from lap_counter import count_turns, naive_count, detect_stops, analyze_laps
from checkout import clock, close_open_sessions, print_receipt, calc_entry_fee, to_mmss


def run_system(seed=7):
    """[메인 처리] 입력 생성 → 태그 처리·매칭 → 50분 일괄 종료 → 키별 턴 감지·안전 알림·기록 분석.
    화면 출력과 저장에 필요한 결과를 딕셔너리로 반환한다."""
    tags, tracks, truth = build_scenario(seed)
    sessions, log = process_tags(tags, tracks)

    # 회차 종료(50분): 퇴장 태그를 잊은 세션 일괄 종료
    for key in close_open_sessions(sessions):
        s = sessions[key]
        log.append((SESSION_MINUTES * 60,
                    f"회차 종료  Key {key} -> 퇴장 태그 없음, 마지막 검출 {clock(s['exit'])} 기준으로 저장"))

    swimmers = []
    for s in sessions.values():
        if s["track"] is None:              # 매칭 실패한 태그는 기록 없음
            continue
        tr = s["track"]
        x_clean = clean_positions(tr["x"])                 # 1) 보간 + 이동평균
        turns = count_turns(tr["t"], x_clean)              # 2) 턴 감지
        alerts = detect_stops(tr["t"], x_clean)            # 3) 안전 알림
        record = analyze_laps(turns, tr["t"][0])           # 4) 기록 분석
        for at, pos in alerts:
            log.append((at, f"안전 알림  Key {s['key']} -> 레인 {pos:.0f}m 지점 정지, 관리자 호출"))
        swimmers.append({
            "key": s["key"], "spec": truth[s["key"]], "session": s,
            "enter": s["enter"], "exit": s["exit"], "status": s["status"],
            "t": tr["t"], "x_raw": tr["x"], "x_clean": x_clean, "y": tr["y"],
            "turns": turns, "alerts": alerts, "record": record,
            "naive": naive_count(tr["x"]), "true": truth[s["key"]]["lengths"],
        })
    swimmers.sort(key=lambda r: r["enter"])
    failed = [s["key"] for s in sessions.values() if s["track"] is None]
    return {"log": sorted(log), "swimmers": swimmers, "failed": failed}


def print_report(result):
    """[화면 출력] 이벤트 로그, 키별 정산서, 정답 대비 정확도 표를 순서대로 출력한다."""
    print("\n[1] 이벤트 로그 (레인 4, 19:00 회차)")
    print("-" * 70)
    for t, msg in result["log"]:
        print(f"  {clock(t)}  {msg}")

    print("\n[2] 퇴장 시 정산서")
    for r in result["swimmers"]:
        print_receipt(r["session"], r["spec"], r["record"], r["alerts"])

    print("\n[3] 정확도 비교 (편도 횟수)")
    print("-" * 56)
    print(f"  {'키 번호':<8}{'정답':>6}{'단순 방향반전':>14}{'제안 알고리즘':>14}  결과")
    for r in result["swimmers"]:
        ok = "일치" if r["true"] == r["record"]["count"] else "불일치"
        print(f"  Key {r['key']:<4}{r['true']:>6}{r['naive']:>14}{r['record']['count']:>14}  {ok}")
    total_true = sum(r["true"] for r in result["swimmers"])
    total_ok = sum(r["true"] for r in result["swimmers"] if r["true"] == r["record"]["count"])
    print(f"  => 제안 알고리즘 {total_ok}/{total_true} 편도 정확히 집계")


def save_results(result, folder="results"):
    """[파일 저장] 키별 기록 CSV, 이벤트 로그 TXT, 그래프 PNG를 folder에 저장한다."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "records.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["락커키", "구분", "회원", "입장", "퇴장", "종료방식", "편도수", "거리(m)",
                    "평균편도", "최고편도", "결제금액", "안전알림"])
        for r in result["swimmers"]:
            sp, rec = r["spec"], r["record"]
            w.writerow([r["key"], sp["age"], "Y" if sp["member"] else "N", clock(r["enter"]), clock(r["exit"]),
                        r["status"], rec["count"], rec["distance"], to_mmss(rec["avg"]), to_mmss(rec["best"]),
                        calc_entry_fee(sp["age"], sp["member"])[2], len(r["alerts"])])
    with open(os.path.join(folder, "event_log.txt"), "w", encoding="utf-8") as f:
        for t, msg in result["log"]:
            f.write(f"{clock(t)}  {msg}\n")
    from viz import setup_korean_font, save_timeline, save_detail
    setup_korean_font()
    save_timeline(result, os.path.join(folder, "lane_timeline.png"))
    save_detail(result["swimmers"][0], os.path.join(folder, "turn_detail.png"))
    print(f"\n[4] 결과 저장 완료 -> {folder}/ (records.csv, event_log.txt, lane_timeline.png, turn_detail.png)")


def main():
    parser = argparse.ArgumentParser(description="락커키 기반 자유수영 랩 자동 카운팅 데모")
    parser.add_argument("--animate", action="store_true", help="레인 애니메이션 창 실행")
    parser.add_argument("--speed", type=int, default=20, help="애니메이션 배속 (기본 20배)")
    parser.add_argument("--gif", action="store_true", help="애니메이션을 results/demo.gif 로 저장")
    parser.add_argument("--seed", type=int, default=7, help="시뮬레이션 난수 시드")
    args = parser.parse_args()

    print("=" * 70)
    print("  락커키 기반 자유수영 랩 자동 카운팅 시스템  (데모: 좌표 시뮬레이션)")
    print("=" * 70)
    result = run_system(args.seed)
    print_report(result)
    save_results(result)

    if args.animate or args.gif:
        from viz import setup_korean_font, animate
        setup_korean_font()
        animate(result, speed=args.speed,
                save_path=os.path.join("results", "demo.gif") if args.gif else None,
                show=args.animate)


if __name__ == "__main__":
    main()
