"""Numeric-drift smoke test: assert the paper's headline strings against
the committed data. Run before every submission-bound compile.

Not exhaustive; guards the numbers a reviewer would check first.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = (ROOT / "paper/main.tex").read_text()
D = ROOT / "docs/paper-data"


def expect(cond: bool, msg: str, errs: list) -> None:
    (errs.append(msg) if not cond else None)



def fmt1(x: float) -> str:
    return f"{x:.1f}"


def dial_sentence(errs: list) -> str:
    """Inference-setting reporting among audited papers with generative heads."""
    path = ROOT / "docs/audit/dial_reporting.jsonl"
    if not path.exists():
        errs.append("docs/audit/dial_reporting.jsonl missing")
        return "\\textbf{MISSING DIAL AUDIT}"
    rows = [json.loads(line) for line in open(path) if line.strip()]
    gen = [r for r in rows if r["action_head"] in ("flow", "diffusion")]
    steps = sum(1 for r in gen if r["denoising_steps_stated"] is True)
    horizon = sum(1 for r in gen if r["exec_horizon_stated"] is True)
    both = sum(1 for r in gen if r["denoising_steps_stated"] is True
               and r["exec_horizon_stated"] is True)
    return (f"Of the ${len(gen)}$ audited papers whose own method uses a flow or "
            f"diffusion action head, ${steps}$ state the denoising step count used "
            f"in evaluation, ${horizon}$ the execution horizon, and at most ${both}$ "
            "both, so the two settings whose effects Sec.~\\ref{sec:transfer} "
            "measures are usually unrecoverable from the paper. ")


def abstract_audit_sentence(eff: dict) -> str:
    """Abstract's audit sentence, from the efficiency-claim audit."""
    return (f"Among ${eff['n_included']}$ VLA efficiency papers claiming parity on LIBERO, "
            f"${round(eff['O1_base_ge_090']['pct'])}\\%$ compare against a base policy at or above "
            f"$90\\%$ success and ${eff['any_uncertainty_or_per_task_or_paired']['k']}$ report any "
            "uncertainty, per-task result, or paired analysis.")


def fr_macros(r3: dict) -> dict:
    """Failure-rate-ratio point and interval macros for the rows the text cites."""
    out = {}
    for key, name in (("pi05_battery", "Bat"), ("pi05_informative", "Inf"),
                      ("pi05_camera_confirmatory", "Cam"), ("pi0_battery", "PiZero")):
        row = r3["failure_ratio"][key]
        out[f"NumFr{name}"] = f"{row['ratio']:.2f}"
        out[f"NumFr{name}Lo"] = f"{row['ci'][0]:.2f}"
        out[f"NumFr{name}Hi"] = f"{row['ci'][1]:.2f}"
    return out


def write_numbers_tex(errs: list) -> dict:
    """Emit paper/numbers.tex so key numerals are generated, never typed."""
    st = json.load(open(D / "step_transfer.json"))
    rows = st["rows"]
    bat, head = rows["pi05_battery"], rows["pi05_headroom_tasks"]
    cur = st["dilution_curve_pi05"]
    cen = json.load(open(D / "dilution_census.json"))
    ctl = cen["size_control"]
    hard = cur[0]
    pi0 = rows["pi0_battery"]
    cc = json.load(open(D / "fusion_shift.json"))["camera_confirmatory"]
    cam_cost = round(100 * (cc["sr_s10"] - cc["sr_s1"]), 1)
    ex = [json.loads(line) for line in open(ROOT / "docs/audit/extraction.jsonl")]
    lib = [c for r in ex for c in r["comparisons"]
           if c["benchmark"] == "LIBERO" and c["rate_x"] is not None and c["rate_y"] is not None]
    ceil = [c for c in lib if min(c["rate_x"], c["rate_y"]) >= 0.90]
    audit = json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))
    p0 = pi0["mcnemar_p"]
    eff = json.load(open(D / "efficiency_audit.json"))
    ver = json.load(open(ROOT / "docs/efficiency_audit/verification_sample.json"))
    if ver.get("manual_resolution", {}).get("fields_confirmed_after_manual") != ver["fields_checked"]:
        errs.append("efficiency verification sample has unresolved fields")
    if eff["O8"]["loss_larger_on_lower_base"] >= eff["O8"]["loss_smaller_on_lower_base"]:
        errs.append("O8 direction changed: rewrite the 'they do not' sentence")
    r3 = json.load(open(D / "failure_ratio_and_shift.json"))
    v1t = json.load(open(D / "v1_varcomp_report.json"))["tasks"]
    other_var_max = max(t["var_init"] + t["e_pq_sampling"] for k, t in v1t.items()
                        if "error" not in t and k != "libero_10/task8")
    vals = {
        "NumBatteryLo": fmt1(bat["ci_pts"][0]),
        "NumBatteryHi": fmt1(bat["ci_pts"][1]),
        "NumSevenLo": fmt1(cur[-2]["ci_pts"][0]),
        "NumSevenHi": fmt1(cur[-2]["ci_pts"][1]),
        "NumHeadroomLo": fmt1(head["ci_pts"][0]),
        "NumHeadroomHi": fmt1(head["ci_pts"][1]),
        "NumHardLo": fmt1(hard["ci_pts"][0]),
        "NumHardHi": fmt1(hard["ci_pts"][1]),
        "NumHeadroomDisc": fmt1(100 * st["certify"]["observed_discordance_rate"]),
        "NumHardDisc": fmt1(100 * st["certify"]["hardest_task_discordance_rate"]),
        "NumCensusPairs": str(cen["n_pairs"]),
        "NumCensusEquiv": str(cen["n_equiv_full"]),
        "NumCensusDiff": str(cen["n_diff_full"]),
        "NumCensusDiffKept": str(cen["n_diff_full_still_diff_informative"]),
        "NumCensusMedian": str(ctl["equiv_kept_median_over_subsets"]),
        "NumCensusNoEight": str(ctl["subsets_without_task8_median_kept"]),
        "NumCensusWithEight": str(ctl["subsets_with_task8_median_kept"]),
        "NumWaldEquiv": str(cen["sensitivity"]["wald_pm5"]["n_equiv_full"]),
        "NumWaldSat": str(cen["sensitivity"]["wald_pm5"]["kept_saturated"]),
        "NumWaldInf": str(cen["sensitivity"]["wald_pm5"]["kept_informative"]),
        "NumUnpEquiv": str(cen["sensitivity"]["unpaired_newcombe_pm5"]["n_equiv_full"]),
        "NumUnpSat": str(cen["sensitivity"]["unpaired_newcombe_pm5"]["kept_saturated"]),
        "NumUnpInf": str(cen["sensitivity"]["unpaired_newcombe_pm5"]["kept_informative"]),
        "NumSevenEquiv": str(cen["sensitivity"]["paired_newcombe_pm7"]["n_equiv_full"]),
        "NumSevenInf": str(cen["sensitivity"]["paired_newcombe_pm7"]["kept_informative"]),
        "NumSevenSat": str(cen["sensitivity"]["paired_newcombe_pm7"]["kept_saturated"]),
        "NumThreeEquiv": str(cen["sensitivity"]["paired_newcombe_pm3"]["n_equiv_full"]),
        "NumStepContrasts": str(cen["by_contrast_kind"]["steps"]["n"]),
        "NumStepEquiv": str(cen["by_contrast_kind"]["steps"]["equiv_full"]),
        "NumStepEquivKept": str(cen["by_contrast_kind"]["steps"]["equiv_kept_informative"]),
        "NumCensusEquivKept": str(ctl["equiv_kept_informative_half"]),
        "NumCensusSatKept": str(ctl["equiv_kept_saturated_half"]),
        "NumAbstractAudit": abstract_audit_sentence(eff),
        "NumEffInc": str(eff["n_included"]),
        "NumEffScreened": str(eff["n_screened"]),
        "NumEffCeil": str(round(eff["O1_base_ge_090"]["pct"])),
        "NumEffCeilNf": str(round(eff["O1b_base_ge_095"]["pct"])),
        "NumEffGap": fmt1(eff["O6_median_gap_pts"]),
        "NumEffAny": str(eff["any_uncertainty_or_per_task_or_paired"]["k"]),
        "NumEffPaired": {1: "one"}.get(eff["O5_paired"]["k"], str(eff["O5_paired"]["k"])),
        "NumEffNoN": str(round(100 - eff["O4_usable_n"]["pct"])),
        "NumEffUsable": str(eff["O7"]["n_usable"]),
        "NumEffCert": str(eff["O7"]["n_certifiable_pm5"]),
        "NumEffCertRatio": str(eff["O7"]["n_certifiable_but_ratio_hi_ge_1_5"]),
        "NumEffLarger": str(eff["O8"]["loss_larger_on_lower_base"]),
        "NumEffPairs": str(eff["O8"]["n_papers_with_lower_base_benchmark"]),
        "NumEffPlotted": str(eff["O1_base_ge_090"]["n"]),
        "NumEffVerAuto": str(ver["fields_confirmed"]),
        "NumEffVerFields": str(ver["fields_checked"]),
        "NumEffVerMiss": str(ver["fields_checked"] - ver["fields_confirmed"]),
        "NumSeedEightLo": fmt1(rows["pi05_envseed8"]["ci_pts"][0]),
        "NumSeedEightHi": fmt1(rows["pi05_envseed8"]["ci_pts"][1]),
        "NumSeedLenDiff": str(round(100 * min(st["envseed_length_differs_share"].values()))),
        "NumRepLenDiff": str(round(100 * st["replicate_cells_length_differs_share"])),
        "NumCertCells": str(cen["certificates_distinct_cells"]),
        "NumHolmDiff": str(cen["n_diff_full_holm"]),
        "NumDiffKeptSat": str(cen["diff_kept_saturated_half"]),
        "NumNinetyEquiv": str(cen["sensitivity"]["paired_newcombe_90pct_pm5"]["n_equiv_full"]),
        "NumNinetySat": str(cen["sensitivity"]["paired_newcombe_90pct_pm5"]["kept_saturated"]),
        "NumNinetyInf": str(cen["sensitivity"]["paired_newcombe_90pct_pm5"]["kept_informative"]),
        "NumPiZeroLo": fmt1(pi0["ci_pts"][0]),
        "NumPiZeroHi": fmt1(pi0["ci_pts"][1]),
        "NumSmolLo": fmt1(rows["smolvla_battery"]["ci_pts"][0]),
        "NumSmolHi": fmt1(rows["smolvla_battery"]["ci_pts"][1]),
        "NumLayoutLo": fmt1(rows["pi05_layout_shift"]["ci_pts"][0]),
        "NumLayoutHi": fmt1(rows["pi05_layout_shift"]["ci_pts"][1]),
        "NumCameraLo": fmt1(rows["pi05_camera_confirmatory"]["ci_pts"][0]),
        "NumCameraHi": fmt1(rows["pi05_camera_confirmatory"]["ci_pts"][1]),
        "NumOtherVarMax": f"{other_var_max:.3f}",
        "NumStepLatency": f"{r3['latency']['step_only_ratio_h10']:.1f}",
        "NumChunkOne": str(r3["latency"]["chunk_ms_s1_h10"]),
        "NumChunkTen": str(r3["latency"]["chunk_ms_s10_h10"]),
        "NumSeedTaskNineA": "--".join(map(str, r3["seed_per_task_discordants"]["seed7"]["9"])),
        "NumSeedTaskNineB": "--".join(map(str, r3["seed_per_task_discordants"]["seed8"]["9"])),
        "NumSubsetsAboveSat": str(r3["census"]["n_subsets_above_saturated"]),
        "NumStepDiff": str(cen["by_contrast_kind"]["steps"]["diff_full"]),
        "NumStepDiffKept": str(cen["by_contrast_kind"]["steps"]["diff_kept_informative"]),
        **fr_macros(r3),
        "NumCamHiA": str(sum(r3["camera_by_level"][k]["s1_only"] for k in ("4", "5"))),
        "NumCamHiB": str(sum(r3["camera_by_level"][k]["s10_only"] for k in ("4", "5"))),
        "NumCamLoA": str(sum(r3["camera_by_level"][k]["s1_only"] for k in ("1", "2", "3"))),
        "NumCamLoB": str(sum(r3["camera_by_level"][k]["s10_only"] for k in ("1", "2", "3"))),
        "NumPiZeroCost": fmt1(abs(pi0["diff_pts"])),
        "NumPiZeroP": f"{p0:.2g}" if p0 >= 1e-4 else "10^{-4}",
        "NumCameraCost": fmt1(cam_cost),
        "NumCertifyPairs": f"{st['certify']['pairs_needed_true_diff_0_power80']:,}".replace(",", "{,}"),
        "NumCertifyHard": f"{st['certify']['hardest_task_pairs_needed_true_diff_0_power80']:,}".replace(",", "{,}"),
        "NumDialSentence": dial_sentence(errs),
        "NumCamHardCost": fmt1(abs(r3["camera_level_groups"]["levels_4_5"]["diff_pts"])),
        "NumCamHardA": str(r3["camera_level_groups"]["levels_4_5"]["s1_only"]),
        "NumCamHardB": str(r3["camera_level_groups"]["levels_4_5"]["s10_only"]),
        "NumCamHardLo": fmt1(r3["camera_level_groups"]["levels_4_5"]["ci_pts"][0]),
        "NumCamHardHi": fmt1(r3["camera_level_groups"]["levels_4_5"]["ci_pts"][1]),
        "NumCamEasyLo": fmt1(r3["camera_level_groups"]["levels_1_3"]["ci_pts"][0]),
        "NumCamEasyHi": fmt1(r3["camera_level_groups"]["levels_1_3"]["ci_pts"][1]),
        "NumEffMedianBase": fmt1(100 * eff["median_base_rate"]),
        "NumEffAllowedRatio": f"{eff['margin5_allowed_failure_ratio_median']:.2f}",
        "NumEffDoubleK": str(eff["margin5_allows_doubling"]["k"]),
        "NumEffDoubleN": str(eff["margin5_allows_doubling"]["n"]),
        "NumEffCeilCount": str(eff["O1_base_ge_090"]["k"]),
        "NumEffSmaller": str(eff["O8"]["loss_smaller_on_lower_base"]),
        "NumEffSignP": f"{eff['O8']['sign_test_p']:.2f}",
        "NumTaskEightShare": str(round(100 * st["task8_share_of_ten_step_failures"])),
        "NumDiscBound": fmt1(100 * ((1 - bat["rate_a"]) + (1 - bat["rate_b"]))),
        "NumDiscObs": fmt1(100 * (bat["a_only"] + bat["b_only"]) / bat["n_pairs"]),
    }
    used = set(re.findall(r"\\(Num[A-Za-z]+)", TEX))
    missing = sorted(u for u in used if u not in vals)
    expect(not missing, f"macros used in main.tex but not generated: {missing}", errs)
    vals = {k: v for k, v in vals.items() if k in used}
    lines = ["% AUTO-GENERATED by scripts/check_paper_numbers.py -- do not edit.",
             "% Single source of truth for data-derived numerals."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in vals.items()]
    out = ROOT / "paper/numbers.tex"
    content = "\n".join(lines) + "\n"
    if not out.exists() or out.read_text() != content:
        out.write_text(content)
        print(f"numbers.tex regenerated ({out})")
    expect("\\input{numbers}" in TEX, "main.tex does not \\input{numbers}", errs)
    return vals


def write_tables(errs: list) -> None:
    """Emit generated tables: the pi0.5 grid and the one-step contrast report."""
    knob = json.load(open(D / "v2_knob_table.json"))
    cells = {(c["num_steps"], c["exec_horizon"]): c for c in knob["cells"]}
    rows = []
    for ns in (1, 2, 5, 10):
        tds = []
        for eh in (1, 5, 10):
            c = cells[(ns, eh)]
            lo, hi = c["ci95"]
            sr = f"{c['success_rate']:.3f}".lstrip("0")
            tds.append(f"{sr} [{lo:.3f}, {hi:.3f}]".replace("0.", "."))
        rows.append(f"${ns}$ & " + " & ".join(tds) + r" \\")
    grid = "\n".join([
        "% AUTO-GENERATED by scripts/check_paper_numbers.py -- do not edit.",
        r"\begin{tabular}{@{}lccc@{}}",
        r"\toprule",
        r"Steps $s$ & $h{=}1$ & $h{=}5$ & $h{=}10$ \\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
    ]) + "\n"
    out = ROOT / "paper/table_grid.tex"
    if not out.exists() or out.read_text() != grid:
        out.write_text(grid)
        print("table_grid.tex regenerated")

    st = json.load(open(D / "step_transfer.json"))
    r3_fr = json.load(open(D / "failure_ratio_and_shift.json"))["failure_ratio"]
    labels = [("pi05_battery", r"$\pi_{0.5}$, battery"),
              ("pi05_non_perfect_tasks", r"\quad without 100\% task"),
              ("pi05_headroom_tasks", r"\quad informative tasks"),
              ("pi05_envseed8", r"$\pi_{0.5}$, env.\ seed 8"),
              ("pi05_layout_shift", r"$\pi_{0.5}$, layout shift"),
              ("pi05_camera_confirmatory", r"$\pi_{0.5}$, camera shift"),
              ("smolvla_battery", r"SmolVLA, battery"),
              ("pi0_battery", r"$\pi_0$, battery")]
    trows = []
    for key, lab in labels:
        r = st["rows"][key]
        lo, hi = r["ci_pts"]
        olo, ohi = r["cond_odds_ratio_ci"]
        fr = r3_fr.get({"pi05_headroom_tasks": "pi05_informative"}.get(key, key))
        fr_cell = (f"${fr['ratio']:.2f}$ $[{fr['ci'][0]:.2f}, {fr['ci'][1]:.2f}]$" if fr else "--")
        trows.append(f"{lab} & ${r['n_pairs']}$ & ${r['a_only']}$--${r['b_only']}$ & "
                     f"${r['diff_pts']:+.1f}$ $[{lo:+.1f}, {hi:+.1f}]$ & "
                     f"${r['cond_odds_ratio']:.2f}$ $[{olo:.2f}, {ohi:.2f}]$ & {fr_cell} \\\\")
    ttbl = "\n".join([
        "% AUTO-GENERATED by scripts/check_paper_numbers.py -- do not edit.",
        r"\begin{tabular}{@{}lrrccc@{}}",
        r"\toprule",
        r"Setting & $n$ & $b$--$c$ & Diff.\ (pts) & Odds ratio $b/c$ & Failure ratio \\",
        r"\midrule",
        *trows,
        r"\bottomrule",
        r"\end{tabular}",
    ]) + "\n"
    out3 = ROOT / "paper/table_transfer.tex"
    if not out3.exists() or out3.read_text() != ttbl:
        out3.write_text(ttbl)
        print("table_transfer.tex regenerated")


def main() -> int:
    errs: list = []
    flat = re.sub(r"\s+", " ", TEX)

    def has(s: str, msg: str) -> None:
        expect(s in flat, f"{msg}: expected {s!r} in tex", errs)

    write_numbers_tex(errs)
    write_tables(errs)
    st = json.load(open(D / "step_transfer.json"))
    rows = st["rows"]

    # --- Sec. dilution ---
    bat = rows["pi05_battery"]
    has(f"${bat['rate_a']:.3f}$ of episodes at one step and ${bat['rate_b']:.3f}$ at ten "
        f"(${bat['a_only']}$--${bat['b_only']}$ discordant pairs, $p{{=}}{bat['mcnemar_p']:.2f}$)", "battery")
    expect(bat["equivalent_at_5"], "battery no longer certifies +/-5", errs)
    head = rows["pi05_headroom_tasks"]
    expect(not head["equivalent_at_5"] and head["tasks"] == [0, 2, 8, 9], "informative subset changed", errs)
    cur = st["dilution_curve_pi05"]
    expect(all(c["ci_pts"][1] >= 5 for c in cur[:-1]), "dilution curve enters margin before the last task", errs)
    ref = st["pi05_reference_task_rates"]
    inf_rates = [round(100 * ref[t]) for t in ("0", "2", "8", "9")]
    has(f"informative tasks succeed in ${inf_rates[0]}$, ${inf_rates[1]}$, ${inf_rates[2]}$, and ${inf_rates[3]}\\%$",
        "informative task rates")
    sat_rates = [round(100 * ref[t]) for t in ("1", "3", "4", "6")]
    has(f"saturated ones in ${min(sat_rates)}$--${max(sat_rates)}\\%$", "saturated task rates")
    cen = json.load(open(D / "dilution_census.json"))
    ctl = cen["size_control"]
    expect(ctl["equiv_kept_saturated_half"] > 3 * max(1, ctl["equiv_kept_informative_half"]), "census asymmetry lost", errs)
    expect(cen["n_diff_full_still_diff_informative"] > cen["diff_kept_saturated_half"], "difference asymmetry lost", errs)
    r3c = json.load(open(D / "failure_ratio_and_shift.json"))
    expect(r3c["census"]["informative_half_is_unique_min"], "informative half no longer unique minimum", errs)
    for key, sv_ in cen["sensitivity"].items():
        if key != "paired_newcombe_pm3":
            expect(sv_["kept_saturated"] > sv_["kept_informative"], f"sensitivity {key} lost asymmetry", errs)
    n_battery_tasks = len(ref)
    has(f"compatible with a ${5 * n_battery_tasks}$-point loss on it", "dilution example")
    has(f"against the ${head['n_pairs']}$ the battery allots", "allotment")

    # --- Sec. transfer ---
    pi0 = rows["pi0_battery"]
    has(f"(${pi0['rate_a']:.3f}$ vs.\\ ${pi0['rate_b']:.3f}$, ${pi0['a_only']}$--${pi0['b_only']}$", "pi0")
    lay = rows["pi05_layout_shift"]
    expect(lay["equivalent_at_5"], "layout no longer equivalent", errs)
    has(f"still succeeds in ${round(100 * lay['rate_b'])}\\%$ of episodes", "layout rate")
    cc = json.load(open(D / "fusion_shift.json"))["camera_confirmatory"]
    has(f"(${cc['s1_only']}$--${cc['s10_only']}$, $p{{=}}0.0008$", "camera overall")
    expect(cc["mcnemar_p"] < 0.001, "camera p changed", errs)
    grp = r3c["camera_level_groups"]
    expect(grp["levels_4_5"]["verdict"] == "DIFFERENT" and grp["levels_1_3"]["verdict"] == "INCONCLUSIVE",
           "camera level-group verdicts changed", errs)

    # --- Sec. audit and report ---
    eff = json.load(open(D / "efficiency_audit.json"))
    expect(eff["O8"]["loss_larger_on_lower_base"] < eff["O8"]["loss_smaller_on_lower_base"], "O8 direction changed", errs)
    fr = r3c["failure_ratio"]["pi05_camera_confirmatory"]
    expect(fr["noninferior_at_1_5"] and fr["ci"][0] > 1, "camera ratio example no longer holds", errs)
    has("would certify non-inferiority at a $1.5$ bound", "ratio bound wording")

    # --- corpus size ---
    n_ep = sum(1 for f in (ROOT / "artifact").rglob("records_*.jsonl") for line in open(f) if line.strip())
    has(f"${n_ep:,}$ per-episode records are released".replace(",", "{,}"), "episode count")

    # --- infrastructure guards kept from earlier passes ---
    import hashlib
    art = ROOT / "artifact"
    if art.exists():
        stale = []
        for src_dir, art_dir in ((D, art / "paper-data"), (ROOT / "docs/audit", art / "audit")):
            for mirror in sorted(p for p in art_dir.iterdir() if p.is_file()):
                src = src_dir / mirror.name
                if src.exists() and hashlib.sha256(src.read_bytes()).hexdigest() != \
                        hashlib.sha256(mirror.read_bytes()).hexdigest():
                    stale.append(mirror.name)
        must_ship = ("recompute_final_50papers.json", "step_transfer.json", "dial_reporting.jsonl",
                     "v1_varcomp_report.json", "v2_knob_table.json")
        missing = [f for f in must_ship
                   if not (art / "audit" / f).exists() and not (art / "paper-data" / f).exists()]
        expect(not stale and not missing,
               "artifact/ stale, rerun scripts/package_artifact.py: "
               + "; ".join(stale + [f"{m} missing" for m in missing])[:200], errs)
    pdf = ROOT / "paper/main.pdf"
    if pdf.exists():
        import os
        newest = max((os.path.getmtime(p) for p in
                      list((ROOT / "paper").glob("*.tex")) + list((ROOT / "paper").glob("*.bib"))
                      + list((ROOT / "paper/figures").glob("*.pdf"))), default=0)
        expect(os.path.getmtime(pdf) >= newest,
               "paper/main.pdf is older than its inputs: rebuild before shipping", errs)
    unc = 100 * json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))["share_not_significant"]
    for doc in (ROOT / "docs/audit/RESULTS.md",):
        if doc.exists():
            expect(f"{unc:.1f}%" in doc.read_text(),
                   f"{doc.name} does not state the current failure rate {unc:.1f}%", errs)

    if errs:
        print("DRIFT DETECTED:")
        for e in errs:
            print(" -", e)
        return 1
    print("all checked numbers consistent with data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
