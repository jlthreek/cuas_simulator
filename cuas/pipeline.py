"""
파이프라인: 시나리오의 각 트랙을 매 스텝 처리 (융합탐지→분류→위협→대응)
"""
import numpy as np
from . import engine

EO_EVIDENCE_WEIGHT = 0.15   # EO 보조증거가 p_uav에 기여하는 최대 가중치(레이더/RF가 주, EO는 보조)


def fuse_detect(obs):
    """① 융합탐지 + ② 오탐저감: SNR 게이트 + RF-레이더 시공간 연관"""
    snr_ok = obs["snr"] > 7
    pos = (obs["radar_x"], obs["radar_y"])
    rf_assoc = False
    if obs["rf_present"] and not np.isnan(obs["rf_x"]):
        rf_assoc = np.hypot(obs["rf_x"] - pos[0], obs["rf_y"] - pos[1]) < 0.6
    return snr_ok, pos, rf_assoc


def track_speed(hist):
    xs = np.array([o["radar_x"] for o in hist]); ys = np.array([o["radar_y"] for o in hist])
    disp = np.hypot(xs[-1] - xs[0], ys[-1] - ys[0]) * 1000.0
    dt = hist[-1]["t"] - hist[0]["t"]
    return disp / dt if dt > 0 else 0.0


def eo_corroborate(ttype, p_uav, hist):
    """EO 카메라 관측(분류신뢰도)을 보조 증거로 결합해 드론 확신도(p_uav)를 보정.
    engine.classify()의 유형판정 임계값 자체는 건드리지 않고, 신뢰도(p_uav)만
    보수적으로 상향 보정한다(레이더/RF 신호가 이미 "드론"으로 판정한 경우에 한해,
    EO가 같은 위치에서 실제로 뭔가를 포착했다면 그 확신을 강화 — corroboration).
    EO 미탐지는 벌점을 주지 않는다(약한 부재증거를 과신하지 않기 위함).
    """
    if ttype != "드론":
        return p_uav
    eo_confs = [o["eo_conf"] for o in hist if o.get("eo_present") and not np.isnan(o["eo_conf"])]
    if not eo_confs:
        return p_uav
    eo_conf = float(np.mean(eo_confs))
    return float(np.clip(p_uav + (1 - p_uav) * EO_EVIDENCE_WEIGHT * eo_conf, 0.0, 1.0))


def wind_alignment(hist, wind_dir):
    if len(hist) < 2:
        return 0.0
    disp = np.array([hist[-1]["x"] - hist[0]["x"], hist[-1]["y"] - hist[0]["y"]])
    if np.linalg.norm(disp) < 1e-6:
        return 0.0
    return float(disp @ np.array(wind_dir) / (np.linalg.norm(disp) * np.linalg.norm(wind_dir) + 1e-9))


def run(scenario, mobile=False, platform_speed=0.0, pop_density=0.5):
    """전체 시뮬레이션 실행. 반환: (timeline rows, per-track final dict)"""
    rows = []; final = {}
    for step in range(len(scenario[0]["traj"])):
        for tgt in scenario:
            obs = tgt["traj"][step]
            conf, pos, rf_assoc = fuse_detect(obs)
            if not conf:
                continue
            hist = tgt["traj"][:step + 1]
            speed = track_speed(hist)
            if mobile:
                speed = abs(speed - platform_speed)   # ③ 자기운동 보정
            rcs = float(np.median([o["rcs"] for o in hist]))
            alt = float(np.median([o["alt"] for o in hist]))
            mdop = any(o["mdop"] for o in hist)
            rf_p = any(o["rf_present"] for o in hist)
            rf_cls = "custom/encrypted" if any(o["rf_class"] == "custom/encrypted" for o in hist) else obs["rf_class"]
            wa = wind_alignment(hist, tgt["wind_dir"])
            ttype, p_uav = engine.classify(rcs, alt, mdop, rf_p, rf_cls, wa)
            eo_detected = any(o.get("eo_present") for o in hist)
            p_uav = eo_corroborate(ttype, p_uav, hist)
            prev = (tgt["traj"][step - 1]["radar_x"], tgt["traj"][step - 1]["radar_y"]) if step > 0 else None
            T, d = engine.assess_threat(pos[0], pos[1], ttype, p_uav, prev, engine_dt_min := (2.0 / 60))
            resp = engine.recommend(T, ttype, pop_density)
            rows.append(dict(step=step, t=obs["t"], tid=tgt["tid"], truth=tgt["truth"],
                             subtype=tgt.get("subtype", ""),
                             x=pos[0], y=pos[1], pred=ttype, p_uav=p_uav, eo_detected=eo_detected,
                             threat=T, d_asset=d, reco=resp["label"], kill=resp["kill"]))
            final[tgt["tid"]] = dict(truth=tgt["truth"], subtype=tgt.get("subtype", ""),
                                     pred=ttype, threat=T, eo_detected=eo_detected,
                                     reco=resp["label"], kill=resp["kill"])
    return rows, final


def accuracy(final):
    kr = {"drone": "드론", "balloon": "풍선", "bird": "새/기타"}
    correct = sum(1 for v in final.values() if v["pred"] == kr.get(v["truth"], ""))
    return correct / len(final) if final else 0.0
