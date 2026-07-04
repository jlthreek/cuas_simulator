"""⑤ 경보 시각화: 상황도 + 위협도 전개 + 대응 경보판 (matplotlib 정적/애니메이션)"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.lines import Line2D
from . import engine

_TCOL = {"drone": "#c0392b", "balloon": "#2980b9", "bird": "#27ae60"}
_TNAME = {"drone": "드론", "balloon": "풍선", "bird": "조류"}
_SUBTYPE_ABBR = {
    "쿼드콥터": "쿼드", "고정익": "고정익", "자폭형(FPV)": "자폭", "회전익(헬기형)": "회전익",
    "오물풍선": "오물", "고고도 미사일 풍선": "고고도",
}


def _set_korean_font():
    import matplotlib.font_manager as fm, os
    for p in ["/System/Library/Fonts/AppleSDGothicNeo.ttc",
              "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "C:/Windows/Fonts/malgun.ttf"]:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            mpl.rcParams["font.family"] = fm.FontProperties(fname=p).get_name()
            break
    mpl.rcParams["axes.unicode_minus"] = False


def render(scenario, rows, final, out_path="dashboard.png"):
    import pandas as pd
    _set_korean_font()
    R = pd.DataFrame(rows)
    kr = {"drone": "드론", "balloon": "풍선", "bird": "새/기타"}
    fig = plt.figure(figsize=(15, 6.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.28)

    # (A) 상황도
    ax = fig.add_subplot(gs[0]); th = np.linspace(0, 2 * np.pi, 100)
    ax.plot(engine.NFZ_R * np.cos(th), engine.NFZ_R * np.sin(th), "--", color="#c0392b", alpha=.5, lw=1)
    for nm, (x, y, r) in engine.ASSETS.items():
        ax.add_patch(plt.Circle((x, y), r, color="#2c3e50", alpha=.15)); ax.plot(x, y, "*", color="#2c3e50", ms=13)
    for tgt in scenario:
        tr = pd.DataFrame(tgt["traj"]); c = _TCOL[tgt["truth"]]
        ax.plot(tr.x, tr.y, "-", color=c, lw=1, alpha=.7); ax.plot(tr.x.iloc[-1], tr.y.iloc[-1], "o", color=c, ms=6)
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5); ax.set_aspect("equal"); ax.grid(alpha=.2)
    ax.set_title("① 다중 침투체 동시 추적", fontsize=10, loc="left")
    ax.set_xlabel("동-서 (km)"); ax.set_ylabel("남-북 (km)")
    ax.legend(handles=[Line2D([0], [0], marker="o", color=c, ls="", label=_TNAME[k]) for k, c in _TCOL.items()] +
              [Line2D([0], [0], marker="*", color="#2c3e50", ls="", label="방호자산")],
              fontsize=7.5, frameon=False, loc="upper right")

    # (B) 위협도 전개
    ax = fig.add_subplot(gs[1])
    for lo, hi, cc in [(0, 45, "#e8f5e9"), (45, 70, "#fff8e1"), (70, 100, "#ffebee")]:
        ax.axhspan(lo, hi, color=cc)
    for tgt in scenario:
        s = R[R.tid == tgt["tid"]]
        ax.plot(s.t, s.threat, "-", color=_TCOL[tgt["truth"]], lw=1.3, alpha=.8)
    ax.set_ylim(0, 100); ax.set_xlabel("시간 (초)"); ax.set_ylabel("위협도")
    ax.set_title("② 트랙별 위협도 전개", fontsize=10, loc="left")

    # (C) 경보판
    ax = fig.add_subplot(gs[2]); ax.axis("off"); ax.set_title("③ 대응 결심 경보판", fontsize=10, loc="left")
    fin = pd.DataFrame(final).T.sort_values("threat", ascending=False); y = 0.95
    ax.text(0.02, y, "트랙   유형(세부)   위협   대응", fontsize=8.5, fontweight="bold"); y -= 0.09
    for tid, r in fin.iterrows():
        col = "#c0392b" if r.kill == "hard" else ("#e67e22" if r.threat >= 45 else "#27ae60")
        sub = _SUBTYPE_ABBR.get(r.get("subtype", ""), "")
        label = f"{r.pred}({sub})" if sub else r.pred
        ax.text(0.02, y, f"{tid}   {label:9}  {float(r.threat):5.0f}   {r.reco[:11]}", fontsize=8, color=col)
        y -= 0.083
    corr = sum(1 for v in final.values() if v["pred"] == kr.get(v["truth"], "")) / len(final)
    ax.text(0.02, 0.03, f"분류정확도 {corr*100:.0f}% · soft-kill 우선", fontsize=8, style="italic", color="#555")
    fig.suptitle("Gray-zone C-UAS 시뮬레이터 대시보드", fontsize=12, fontweight="bold", y=1.02)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return out_path
