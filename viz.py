# ============================================================
#  viz.py - 결과 그래프 저장과 데모용 레인 애니메이션
# ============================================================

import numpy as np
import matplotlib
from matplotlib import font_manager
from config import LANE_LENGTH, WALL_ZONE, SESSION_MINUTES
from checkout import clock

COLORS = ["#0096B7", "#E85D04", "#2A9D8F", "#7B2CBF", "#D62828"]


def setup_korean_font():
    """[그래프 보조] 컴퓨터에 설치된 한글 글꼴을 찾아 matplotlib에 지정한다(Windows/Mac/Linux)."""
    names = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]:
        if name in names:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def save_timeline(result, path):
    """[결과 저장] 모든 수영자의 레인 위치를 시간축에 그리고, 턴 감지와 안전 알림을 표시해 저장한다."""
    import matplotlib.pyplot as plt
    rows = [r for r in result["swimmers"]]
    fig, axes = plt.subplots(len(rows), 1, figsize=(11, 1.55 * len(rows) + 0.6), dpi=160, sharex=True)
    for ax, r, c in zip(axes, rows, COLORS):
        t = r["t"] / 60
        ax.axhspan(LANE_LENGTH - WALL_ZONE, LANE_LENGTH + 1, color="#DDEFF5", lw=0)
        ax.axhspan(-1, WALL_ZONE, color="#DDEFF5", lw=0)
        ax.plot(t, r["x_clean"], color=c, lw=1.1)
        turns = np.array(r["turns"])
        if len(turns):
            ax.plot(turns / 60, np.interp(turns, r["t"], r["x_clean"]), "o", ms=3.5, color="#14283C")
        for at, pos in r["alerts"]:
            ax.plot(at / 60, pos, marker="^", ms=10, color="#D62828")
        ax.set_ylim(-1, LANE_LENGTH + 1)
        ax.set_yticks([0, 25])
        ax.set_ylabel(f"Key {r['key']}", rotation=0, ha="right", va="center", fontsize=10)
        ax.text(1.005, 0.5, f"{len(r['turns'])}회", transform=ax.transAxes, va="center", fontsize=10, weight="bold")
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("회차 시작 후 경과 시간 (분)")
    axes[0].set_title("레인 위치와 턴 감지 (●: 턴, ▲: 안전 알림)", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_detail(r, path, start_min=0, minutes=4):
    """[결과 저장] 한 사람의 원본 좌표와 보간·평활화 결과를 확대해 비교하는 그래프를 저장한다."""
    import matplotlib.pyplot as plt
    t0 = r["t"][0] + start_min * 60
    m = (r["t"] >= t0) & (r["t"] <= t0 + minutes * 60)
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=180)
    ax.axhspan(LANE_LENGTH - WALL_ZONE, LANE_LENGTH + 1, color="#DDEFF5", lw=0)
    ax.axhspan(-1, WALL_ZONE, color="#DDEFF5", lw=0)
    ax.plot(r["t"][m] - r["t"][0], r["x_raw"][m], ".", ms=2, color="#AAB6C0", label="카메라 원본 (노이즈·끊김)")
    ax.plot(r["t"][m] - r["t"][0], r["x_clean"][m], color="#14283C", lw=1.5, label="보간 + 이동평균")
    tt = np.array([x for x in r["turns"] if t0 <= x <= t0 + minutes * 60])
    ax.plot(tt - r["t"][0], np.interp(tt, r["t"], r["x_clean"]), "o", color="#0096B7", ms=6, label="턴 감지")
    ax.set_ylim(-1, LANE_LENGTH + 1)
    ax.set_xlabel("입장 후 경과 시간 (초)")
    ax.set_ylabel("레인 위치 (m)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def animate(result, speed=20, save_path=None, show=True):
    """[데모] 레인을 위에서 본 화면에 수영자를 움직이며 랩 수·상태·안전 알림을 실시간으로 보여준다.
    speed: 실제 시간 대비 재생 배속, save_path: GIF로 저장할 경로(선택)."""
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.patches import Rectangle

    sw = result["swimmers"]
    end_t = max(r["exit"] for r in sw) + 15
    play_fps = 10
    frames = list(np.arange(0, end_t, speed / play_fps)) + [SESSION_MINUTES * 60] * 25

    fig = plt.figure(figsize=(11, 5.6), dpi=100)
    ax = fig.add_axes([0.04, 0.42, 0.92, 0.42])
    board = fig.add_axes([0.04, 0.03, 0.92, 0.34])
    board.axis("off")
    ax.add_patch(Rectangle((0, -1.25), LANE_LENGTH, 2.5, color="#BFE6F0"))
    for wx in (0, LANE_LENGTH - WALL_ZONE):
        ax.add_patch(Rectangle((wx, -1.25), WALL_ZONE, 2.5, color="#9ED8E8"))
    ax.plot([0.5, LANE_LENGTH - 0.5], [0, 0], color="#14283C", lw=4, alpha=0.35)   # 바닥 레인 라인
    for i in range(0, 26, 5):
        ax.text(i, -1.55, f"{i}m", ha="center", va="top", fontsize=8, color="#4A6070")
    ax.text(-0.3, 0, "입구\n(RFID)", ha="right", va="center", fontsize=9, color="#14283C", weight="bold")
    ax.set_xlim(-2.2, LANE_LENGTH + 0.6)
    ax.set_ylim(-2.0, 1.6)
    ax.axis("off")
    title = fig.text(0.04, 0.93, "", fontsize=15, weight="bold", color="#14283C")
    ticker = fig.text(0.04, 0.88, "", fontsize=10, color="#4A6070")

    dots, labels = [], []
    for r, c in zip(sw, COLORS):
        d, = ax.plot([], [], "o", ms=16, color=c, mec="white", mew=2)
        lb = ax.text(0, 0, f"{r['key']}", ha="center", va="center", fontsize=7, color="white", weight="bold")
        dots.append(d)
        labels.append(lb)
    rows = []
    for i, (r, c) in enumerate(zip(sw, COLORS)):
        y = 0.85 - i * 0.22
        board.text(0.0, y, "●", color=c, fontsize=14, va="center", transform=board.transAxes)
        # 칸별로 위치를 고정해 글꼴과 상관없이 줄이 맞도록 함: 키 / 편도 / 거리 / 상태
        rows.append([board.text(x0, y, "", fontsize=12, va="center", ha=ha, transform=board.transAxes)
                     for x0, ha in [(0.03, "left"), (0.22, "right"), (0.31, "right"), (0.36, "left")]])
    log = sorted(result["log"])

    def draw(t):
        title.set_text(f"레인 4  자유수영 {clock(0)[:5]} 회차   현재 {clock(t)}   (x{speed} 배속)")
        recent = [m for tt, m in log if tt <= t]
        ticker.set_text(("최근 이벤트: " + recent[-1]) if recent else "최근 이벤트: -")
        for i, (r, d, lb, row) in enumerate(zip(sw, dots, labels, rows)):
            inside = r["t"][0] <= t <= r["t"][-1]
            laps = sum(1 for x in r["turns"] if x <= t)
            alert = any(a <= t <= a + 6 for a, _ in r["alerts"])
            if inside:
                x = float(np.interp(t, r["t"], r["x_clean"]))
                y = float(np.interp(t, r["t"], r["y"]))
                d.set_data([x], [y])
                lb.set_position((x, y))
                d.set_color("#D62828" if alert else COLORS[i])     # 안전 알림 중이면 빨간색
            else:
                d.set_data([], [])
                lb.set_position((-50, -50))
            if t < r["enter"]:
                state = "대기"
            elif t >= r["exit"]:
                state = r["status"]
            elif alert:
                state = "!! 안전 알림 - 관리자 확인"
            else:
                state = "수영 중"
            for cell, text in zip(row, [f"Key {r['key']}", f"{laps}회", f"{laps * 25}m", state]):
                cell.set_text(text)
                cell.set_color("#D62828" if alert else "#14283C")
        return dots + labels + [c for row in rows for c in row] + [title, ticker]

    anim = FuncAnimation(fig, draw, frames=frames, interval=1000 / play_fps, blit=False, repeat=False)
    if save_path:
        anim.save(save_path, writer="pillow", fps=play_fps)
    if show:
        plt.show()
    plt.close(fig)
