import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fb16 import *
import copy, time
SCR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blend(img8, g_):
    q = np.clip(np.rint(g_[2] * 255), 0, 255) / 255.0
    if len(g_) > 4 and g_[4] == "multiply":
        return np.clip(np.rint(img8.astype(np.float64) * q), 0, 255).astype(np.uint8)
    return screen(img8, q)


def rel(p):
    return os.path.relpath(p, REPO)


def save(img, p):
    Image.fromarray(img).save(p, optimize=False, compress_level=6)
    return rel(p)


def run(key, test=True):
    t0 = time.time()
    cfg, st = load(key)
    fcfg = F.ROOMS[key]
    fid = fcfg.get("frame_id") or st["cfg"].get("frame_id") or key
    base, layers, lights = F.read_stack(st)
    H, W = base.shape[:2]
    fin15 = np.asarray(Image.open(os.path.join(R, cfg["finish"])).convert("RGB"))
    fm = F.frame_mask((H, W), st["frame_box"])
    ids, leg, cam, Z = idmap(cfg), legend(cfg), camera(cfg), depth(cfg)
    reg = region_of(layers, lights, (H, W))
    pm = plaster_mask(ids, leg, reg, ids_override=cfg.get("plaster_ids")) & fm
    rec = dict(room=key, frame=fid, date=DATE, brief=BRIEF, spec=SPEC, start=dict(manifest=cfg["manifest"], finish_frame=cfg["finish"]),
               before=measure(fin15, pm, fm), targets=dict(plaster_L=cfg["t"]["Lr"], plaster_b=cfg["t"]["br"], aim=dict(L=cfg["t"]["L"], a=cfg["t"]["a"], b=cfg["t"]["b"]), black=list(BLACK)))
    # (c) the grade, fitted on the room's latest finished frame
    lut, grec = fit_grade(fin15, pm, fm, cfg["t"])  # lut = the grade parameters (Lab)
    rec["grade"] = grec
    # (a) the outside
    al = np.zeros((H, W))
    base16 = base
    n_in = dpl = None
    if cfg.get("outside") or cfg.get("glow"):
        n_in, dpl, rec["window_plane"] = window_plane(cfg, cam, Z, ids, leg)
    if cfg.get("outside"):
        kind = "west" if cfg["outside"] in ("west", "living", "west-hall") else cfg["outside"]
        al, rec["outside_mask"] = outside_alpha(ids, leg, base, cfg.get("outside_ids"), cfg.get("frame_ids"))
        O, rec["outside"] = sample_outside(kind, cam, n_in, al, cfg.get("az_off", 0.0))
        Oc, rec["outside"]["calibration"] = calibrate_outside(O, al, kind)
        if cfg["outside"] == "living":
            import warp16 as WP
            V8, cov, region, wrec, hids = WP.living_view(cfg["frame"])
            view, frec = WP.fill_view(V8, cov, region, hids, fin15)
            ra = cv2.GaussianBlur(region.astype(np.float64), (0, 0), 0.7)
            Oc = np.where(region[..., None], view, Oc)
            al = np.maximum(al, ra)
            rec["living_view"] = dict(wrec, **frec, rule="the living room through the opening = the M0-W frame (0 stop vs H-W); the grade is inverted under it so it lands unchanged")
        Opre = inv_grade(Oc, lut)
        base16 = np.clip(np.rint(base * (1 - al[..., None]) + Opre * al[..., None]), 0, 255).astype(np.uint8)
        over = {}
        for (L, S), e in zip(layers, st["entries"]):
            a = L[..., 3][al > 0.5]
            if (a > 0).mean() > 0.02:
                over[e["name"]] = dict(frac=round(float((a > 0).mean()), 3), opaque_frac=round(float((a == 255).mean()), 3))
        rec["outside"]["layers_over_the_window"] = over
    # the finished frame with the new plate: fin15 + T (base16 - base), T = what of the plate reaches the frame
    ones = np.full_like(base, 255)
    T = (F.compose(ones, layers, lights).astype(np.float64) - F.compose(np.zeros_like(base), layers, lights).astype(np.float64)) / 255.0
    d = base16.astype(np.float64) - base.astype(np.float64)
    fin_pre = np.clip(np.rint(fin15 + T * d), 0, 255).astype(np.uint8)
    gcache = {}
    black_t = BLACK_T
    for it_b in range(4):
        if it_b:
            lut, grec = fit_grade(fin_pre, pm, fm, cfg["t"], black_t)
            rec["grade"] = grec
        graded = apply_grade(fin_pre, lut)
        # glows (screen over the whole graded composite)
        glows = []
        gwin = np.zeros((H, W))
        pt = lab2rgb(cfg["t"]["L"], cfg["t"]["a"], cfg["t"]["b"])
        if cfg.get("glow") == "fluted":
            gid = [k for k, v in leg.items() if "fluted glass" in v.lower()]
            gm = cv2.erode(np.isin(ids, gid).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float64)
            gm = cv2.GaussianBlur(gm, (0, 0), 1.5)
            al_src = (gm > 0.5).astype(np.float64)
            g = gcache.get('w') if 'w' in gcache else gcache.setdefault('w', window_glow(cam, Z, al_src, n_in, dpl, H, W)); gwin = np.maximum(g, gm)
            A = glow_amp(pt, 3.5)
            Sg = g[..., None] * A * WARM
            Lg_ = lab(graded)[..., 0]
            gm = (cv2.dilate(np.isin(ids, gid).astype(np.uint8), np.ones((45, 45), np.uint8)) > 0) & (Lg_ > 55) & ~reg
            gm = cv2.morphologyEx(gm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float64)
            gm = cv2.GaussianBlur(gm, (0, 0), 1.0)
            med = np.median(graded[(gm > 0.9) & ~reg].astype(float), 0)
            tgt = lab2rgb(84.0, 3.0, 14.0)
            k_ = np.clip(tgt / np.maximum(med, 1), 0, 1)
            sc = k_
            Mglass = 1 - (gm * (1 - reg))[..., None] * (1 - k_)
            glows.append(("window-glow", "(b) fluted glass: warm, +1/6 stop around the window", Sg, None))
            glows.append(("glass-tint", "(b) the fluted glass to L 84 / b* 14 (the bounce from the sunlit court wall): multiply, the glass only", Mglass, None, "multiply"))
            rec["glass"] = dict(ids=gid, median_graded_before_tint=[round(v, 1) for v in med], multiply=[round(float(v), 3) for v in sc], glow_amp=round(A, 4))
        elif cfg.get("glow"):
            g = gcache.get('w') if 'w' in gcache else gcache.setdefault('w', window_glow(cam, Z, al, n_in, dpl, H, W)); gwin = g
            A = glow_amp(pt, 3.5)
            glows.append(("window-glow", "(b) window glow: area source from the clay (irradiance, and the near field within about 1 m), low frequency, +3.5 L on the shade plaster at full strength", g[..., None] * A * WARM, None))
            rec["window_glow"] = dict(amp=round(A, 4), color=WARM.tolist(), dL_full_on_plaster=3.5, near_field="1 / (1 + (d / 1.1 m)^4)", blur_px=25)
        Lpre = lab(fin_pre)[..., 0]
        lamp_rows = []
        for (L, S), e in zip(layers, st["entries"]):
            if not P.is_lamp(e["slot"]):
                continue
            a = L[..., 3]
            if e["slot"] in (cfg.get("lamps") or []):
                s, info = sconce_glow(a, H, W, 0.22)
                s = s + lamp_restore(fin_pre, graded, a, Lpre, cfg.get("emit_lo", 84.0))
                glows.append((f"{e['product']}", f"(d) {e['slot']}: was NOT lit; warm body + wall pool", np.clip(s, 0, 0.95), e))
                lamp_rows.append(dict(slot=e["slot"], how="sconce glow + emitter keep", **info))
            else:
                s = lamp_restore(fin_pre, graded, a, Lpre, cfg.get("emit_lo", 84.0))
                if s.max() > 0.01:
                    glows.append((f"{e['product']}", f"(d) {e['slot']}: the emitting shade keeps its pre-grade brightness (it is the source)", s, e))
                    lamp_rows.append(dict(slot=e["slot"], how="emitter keep", px=int((s.max(2) > 0.01).sum())))
        if cfg.get("outside") and cfg.get("glow") is True:
            win = cv2.dilate((al > 0.3).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
            for (L, S), e in zip(layers, st["entries"]):
                if e["slot"] in ("curtains", "roman-blind", "blind", "sheer-curtains"):
                    a = L[..., 3].astype(np.float64) / 255.0
                    m = cv2.GaussianBlur((win * a).astype(np.float64), (0, 0), 6) * a
                    if m.max() > 0.02:
                        A2 = glow_amp(pt, 4.0)
                        glows.append((f"{e['product']}", f"(b) {e['slot']}: the fabric over the glass, backlit by the window (+4 L)", m[..., None] * A2 * WARM, e))
                        lamp_rows.append(dict(slot=e["slot"], how="fabric backlight over the glass", px=int((m > 0.02).sum())))
        rec["lamps"] = lamp_rows
        fq = graded.copy()
        for g_ in glows:
            fq = blend(fq, g_)
        p05 = float(np.percentile(lab(fq)[..., 0][fm], 0.5))
        rec["grade"]["black_loop"] = dict(iteration=it_b + 1, black_target_in_fit=round(black_t, 2), p05_final=round(p05, 2))
        if abs(p05 - BLACK_T) < 0.25:
            break
        black_t += BLACK_T - p05
    # quantize glows to the files, compose the final frame
    final = graded.copy()
    gfiles = []
    mp = os.path.join(R, cfg["manifest"]); mdir = os.path.dirname(mp)
    os.makedirs(os.path.join(mdir, "light"), exist_ok=True)
    gsum = np.zeros((H, W)); glamp = np.zeros((H, W))
    for g_ in glows:
        name, note, s, e = g_[:4]; mode = g_[4] if len(g_) > 4 else "screen"
        q = np.clip(np.rint(s * 255), 0, 255).astype(np.uint8)
        dup = e is not None and sum(1 for x in st["entries"] if x.get("product") == e.get("product")) > 1
        fn = os.path.join(mdir, "light", f"{name}-{fid}-fb16.png" if name == "window-glow" else (f"{name}-{e['name']}-fb16.png" if dup else f"{name}-fb16.png"))
        save(q, fn)
        final = blend(final, g_)
        gsum = np.maximum(gsum, (q.max(2) if mode == "screen" else 255 - q.min(2)) / 255.0)
        if e is not None:
            glamp = np.maximum(glamp, q.max(2) / 255.0)
        gfiles.append(dict(file=os.path.relpath(fn, mdir), blend=mode, over="the whole graded composite (not x keep)", note=note,
                           product=(e or {}).get("product"), slot=(e or {}).get("slot"), px=int((q.max(2) > 0).sum())))
    # files
    od = os.path.join(R, fcfg["out_dir"]); on = fcfg["out_name"]
    files = []
    if cfg.get("outside"):
        bfile = os.path.join(os.path.dirname(st["base"]), os.path.basename(st["base"]).replace(".png", "-fb16.png"))
        files.append(save(base16, bfile))
    ffin = os.path.join(od, on + "-fb16-finish.png"); files.append(save(final, ffin))
    ffr = os.path.join(od, on + "-fb16-frame.png"); files.append(save(F.frame_view(final, st), ffr))
    files += [rel(os.path.join(mdir, g["file"])) for g in gfiles]
    # manifest-fb16
    m16p = mp.replace(".json", "").replace("-fb15", "") + "-fb16.json"
    man = json.load(open(m16p)) if os.path.exists(m16p) else json.load(open(mp))
    if cfg.get("outside"):
        if "bases" in man and fcfg.get("frame_id"):
            k_ = fcfg["frame_id"]; old = F._png_of(man["bases"][k_])
            if not old.endswith("-fb16.png"):
                man["bases"][k_] = man["bases"][k_].replace(old, old.replace(".png", "-fb16.png"))
        else:
            old = F._png_of(man["base"])
            if not old.endswith("-fb16.png"):
                man["base"] = man["base"].replace(old, old.replace(".png", "-fb16.png"))
    fb = man.setdefault("fb16", dict(date=DATE, brief=BRIEF, spec=SPEC, previous=os.path.basename(mp), tool="assets/renders/tools/fb16/ (run16.py, fb16.py)",
                                     compose="the previous formula on the fb16 base; then L0: the grade (frames.<id>.grade, Lab, analytic) on the composite, then each glow screened over the whole composite (not x keep). Products are not redrawn: every layer and shadow file is the previous one",
                                     frames={}))
    fb["frames"][fid] = dict(grade={k_: v for k_, v in lut.items() if k_ != "fit"} | dict(fit=grec), glows=gfiles, outside=rec.get("outside"),
                             base=os.path.relpath(bfile, mdir) if cfg.get("outside") else None)
    for g in gfiles:
        if g.get("product"):
            for row in man.get("layers", []):
                if row.get("product") == g["product"] and row.get("default") and (not fcfg.get("frame_id") or row.get("frame") == fcfg.get("frame_id")):
                    row["glow_fb16"] = dict(file=g["file"], blend="screen", over="whole graded composite")
    json.dump(man, open(m16p, "w"), ensure_ascii=False, indent=1)
    files.append(rel(m16p))
    # checks
    chg_pre = np.abs(fin_pre.astype(int) - fin15.astype(int)).max(2) > 0
    stack15 = F.compose(base, layers, lights); stack16 = F.compose(base16, layers, lights)
    chg_st = np.abs(stack16.astype(int) - stack15.astype(int)).max(2) > 0
    g15 = apply_grade(fin15, lut)
    chg_fin = np.abs(final.astype(int) - g15.astype(int)).max(2) > 0
    changed = (al > 0) | (gsum > 0)
    re_final = apply_grade(np.clip(np.rint(fin15 + T * (np.asarray(Image.open(bfile).convert("RGB")).astype(np.float64) - base)), 0, 255).astype(np.uint8) if cfg.get("outside") else fin15, lut)
    for g in gfiles:
        q_ = np.asarray(Image.open(os.path.join(mdir, g["file"])).convert("RGB")).astype(np.float64)
        re_final = screen(re_final, q_ / 255.0) if g["blend"] == "screen" else np.clip(np.rint(re_final * (q_ / 255.0)), 0, 255).astype(np.uint8)
    rec["rnd2"] = dict(rule="outside the changed regions (the window alpha, the glows): the frame = the grade of the fb15 frame, pixel for pixel; before the grade only the window changes",
                       finish_before_grade_outside_window_px=int((chg_pre & ~(al > 0)).sum()),
                       stack_outside_window_px=int((chg_st & ~(al > 0)).sum()),
                       final_vs_graded_fb15_outside_changed_px=int((chg_fin & ~changed).sum()),
                       changed_region_px=int(changed.sum()), reproduced_from_files_max=int(np.abs(re_final.astype(int) - final.astype(int)).max()))
    quiet = pm & (glamp == 0)
    rec["after"] = measure(final, quiet, fm)
    if cfg.get("glow") and cfg.get("glow") != "fluted":
        zone = pm & (cv2.resize(cv2.GaussianBlur((al > 0).astype(np.float32), (0, 0), 1), (W, H)) == 0)
        gz = window_glow  # noqa
        near = fm & (gwin >= 0.5) & (glamp == 0) & (al == 0)
        if near.sum() > 500:
            Lf, Lg = lab(final)[near], lab(g15)[near]
            npl = near & pm
            rec["after"]["window_zone_plaster"] = dict(px=int(npl.sum()), dL_median=round(float(np.median(lab(final)[npl][:, 0] - lab(g15)[npl][:, 0])), 2) if npl.sum() > 200 else None,
                                                     b_median=round(float(np.median(lab(final)[npl][:, 2])), 2) if npl.sum() > 200 else None)
            rec["after"]["window_zone"] = dict(rule="every surface where the window field is at least half its full value", px=int(near.sum()), dL_median=round(float(np.median(Lf[:, 0] - Lg[:, 0])), 2), dL_p90=round(float(np.percentile(Lf[:, 0] - Lg[:, 0], 90)), 2), b_median=round(float(np.median(Lf[:, 2])), 2))
    if cfg.get("outside"):
        Lb = lab(final); mm = (al > 0.5) & (T.mean(2) > 0.9); thr = np.percentile(Lb[..., 0][mm], 70); sky = mm & (Lb[..., 0] >= thr)
        rec["after"]["outside"] = dict(L_p90=round(float(np.percentile(Lb[..., 0][mm], 90)), 1), L_p10=round(float(np.percentile(Lb[..., 0][mm], 10)), 1),
                                       light_part_ab=[round(float(np.median(Lb[..., i][sky])), 1) for i in (1, 2)])
    if cfg.get("glow") == "fluted":
        Lb = lab(final); gm2 = np.isin(ids, rec["glass"]["ids"]) & ~reg
        rec["after"]["glass_lab"] = [round(float(np.median(Lb[..., i][gm2])), 1) for i in range(3)]
    if test:
        base_g = apply_grade(base16, lut)
        lg = [(np.concatenate([apply_grade(Lr[..., :3], lut), Lr[..., 3:]], 2), Sr) for Lr, Sr in layers]
        for g_ in glows:
            _s, _e = g_[2], g_[3]
            if _e is not None:
                i_ = st["entries"].index(_e)
                q_ = np.clip(np.rint(_s * 255), 0, 255) / 255.0
                lg[i_] = (np.concatenate([screen(lg[i_][0][..., :3], q_), lg[i_][0][..., 3:]], 2), lg[i_][1])
        tr = P.run_test(st, base_g, lg, lights, "fb16")
        rows = tr["rows"]
        rec["pasted_test"] = dict(on="the graded fb16 stack before the shared finish (grade on the plate and every layer, lamp glows on their layers); compare with fb15 score_fb15_before_finish", score=round(sum(r.get("score", 0) for r in rows), 2),
                                  per_layer_mean=round(sum(r.get("score", 0) for r in rows) / max(1, len(rows)), 2),
                                  lamps={r["layer"]: (r.get("lamp") or {}).get("verdict") if isinstance(r.get("lamp"), dict) else r.get("lamp") for r in rows if r.get("lamp") is not None},
                                  worst=sorted([(r["layer"], r.get("score", 0)) for r in rows], key=lambda x: -x[1])[:3])
    rec["files"] = files
    rec["seconds"] = round(time.time() - t0, 1)
    cp = os.path.join(od, on + "-fb16-checks.json")
    json.dump(rec, open(cp, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(room=key, before=rec["before"], after=rec["after"], rnd2=rec["rnd2"], lamps=lamp_rows, test=rec.get("pasted_test", {}).get("per_layer_mean"),
                          lamp_test=rec.get("pasted_test", {}).get("lamps"), over=(rec.get("outside") or {}).get("layers_over_the_window"), sec=rec["seconds"]), ensure_ascii=False))


if __name__ == "__main__":
    test = "--no-test" not in sys.argv
    for k in [a for a in sys.argv[1:] if not a.startswith("--")]:
        run(k, test)
