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
    }
    lines = ["% AUTO-GENERATED by scripts/check_paper_numbers.py -- do not edit.",
             "% Single source of truth for data-derived numerals."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in vals.items()]
    out = ROOT / "paper/numbers.tex"
    content = "\n".join(lines) + "\n"
    if not out.exists() or out.read_text() != content:
        out.write_text(content)
        print(f"numbers.tex regenerated ({out})")
    expect("\\input{numbers}" in TEX, "main.tex does not \\input{numbers}", errs)
    for k in vals:
        expect(f"\\{k}" in TEX, f"macro \\{k} generated but unused in main.tex", errs)
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
    expect(r"\input{table_transfer}" in TEX, "main.tex does not input table_transfer", errs)


def main() -> int:
    errs: list = []
    flat = re.sub(r"\s+", " ", TEX)

    def has(s: str, msg: str) -> None:
        expect(s in flat, f"{msg}: expected {s!r} in tex", errs)

    write_numbers_tex(errs)
    write_tables(errs)
    st = json.load(open(D / "step_transfer.json"))
    rows = st["rows"]

    # --- Sec. dilution: the battery contrast and the ceiling mechanism ---
    bat = rows["pi05_battery"]
    has(f"${bat['rate_a']:.3f}$ of episodes at one step and ${bat['rate_b']:.3f}$", "battery rates")
    has(f"(${bat['a_only']}$--${bat['b_only']}$ discordant pairs, $p{{=}}{bat['mcnemar_p']:.2f}$)",
        "battery discordants/p")
    expect(bat["equivalent_at_5"] and bat["equivalent_at_5_cluster"],
           "battery no longer certifies +/-5", errs)
    cur = st["dilution_curve_pi05"]
    last, prev = cur[-1], cur[-2]
    expect(last["discordant"] == prev["discordant"] and last["added_task_ref_rate"] == 1.0,
           "last admitted task is no longer a perfectly solved task adding no discordance", errs)
    expect(all(c["ci_pts"][1] >= 5 for c in cur[:-1]),
           "dilution curve (95% rule) enters the margin before the last task", errs)
    first90 = next(i for i, c in enumerate(cur) if -5 < c["ci90_pts"][0] and c["ci90_pts"][1] < 5)
    expect(first90 == len(cur) - 2, "90% rule no longer certifies exactly one task earlier", errs)
    has(f"adds ${last['n_pairs'] - prev['n_pairs']}$ pairs and no discordant one", "fig caption pairs")
    has(f"adds ${last['n_pairs'] - prev['n_pairs']}$ pairs, no discordant ones", "text pairs")
    ref = st["pi05_reference_task_rates"]
    near = [v for v in ref.values() if 0.95 <= v < 1.0]
    words = "one two three four five six seven eight".split()
    expect(sum(1 for v in ref.values() if v >= 1.0) == 1 and round(min(ref.values()), 2) == 0.80,
           "battery reference rates changed (one perfect task, hardest 0.80)", errs)
    has(f"{words[len(near) - 1]} battery tasks succeed in $95$--${round(100 * max(near))}\\%$", "ceiling counts")
    hard_row = st["rows"]["pi05_battery"]["per_task"]["8"]
    has(f"with ${hard_row['a_only']}$ discordant pairs won by one step and ${hard_row['b_only']}$ by ten",
        "task 8 discordants")
    head = rows["pi05_headroom_tasks"]
    cen = json.load(open(D / "dilution_census.json"))
    expect(head["tasks"] == cen["informative_tasks"] == [0, 2, 8, 9],
           "informative task set differs between analyses", errs)
    has(f"informative tasks ($n{{=}}{head['n_pairs']}$)", "informative subset n")
    expect(not head["equivalent_at_5"] and not rows["pi05_non_perfect_tasks"]["equivalent_at_5"],
           "restricted subsets now certify +/-5", errs)
    has(f"against the ${head['n_pairs']}$ the battery allots", "text allotment")
    ctl = cen["size_control"]
    expect(ctl["equiv_kept_saturated_half"] > 3 * max(1, ctl["equiv_kept_informative_half"]),
           "census control no longer shows saturated >> informative for equivalences", errs)
    expect(cen["n_diff_full_still_diff_informative"] > cen["diff_kept_saturated_half"],
           "informative half no longer keeps more differences than saturated half", errs)
    for key, sv_ in cen["sensitivity"].items():
        if key == "paired_newcombe_pm3":
            continue
        expect(sv_["kept_saturated"] > sv_["kept_informative"],
               f"census sensitivity {key} no longer shows saturated > informative", errs)
    expect(set(cen["certificates_by_grid"]) == {"pi05_seed7", "pi05_seed8", "pi0_seed7"}
           and cen["certificates_by_grid"]["pi0_seed7"] == 0, "certificates no longer all pi0.5", errs)
    n_sub = len(head["tasks"]) * 60
    expect(n_sub == head["n_pairs"], "four-task subset size is no longer 240 pairs", errs)
    has(f"has the same ${n_sub}$ pairs", "subset size")
    has(f"$\\NumCensusEquivKept$ equivalence and", "singular equivalence wording")
    expect(ctl["equiv_kept_informative_half"] == 1, "informative-half equivalence count no longer 1 (fix grammar)", errs)
    kt = {(c["num_steps"], c["exec_horizon"]): c for c in json.load(open(D / "v2_knob_table.json"))["cells"]}
    lat_d, lat_f = kt[(10, 5)]["measured_latency_ms_per_step"], kt[(1, 10)]["measured_latency_ms_per_step"]

    # --- Sec. transfer ---
    pi0 = rows["pi0_battery"]
    has(f"${pi0['rate_a']:.3f}$ vs.\\ ${pi0['rate_b']:.3f}$, ${pi0['a_only']}$--${pi0['b_only']}$",
        "pi0 contrast")
    sv = rows["smolvla_battery"]
    has(f"(${sv['rate_a']:.3f}$ vs.\\ ${sv['rate_b']:.3f}$,", "smolvla rates")
    has(f"$p{{=}}{sv['mcnemar_p']:.2f}$", "smolvla p")
    lay = rows["pi05_layout_shift"]
    has(f"(${lay['rate_a']:.3f}$ vs.\\ ${lay['rate_b']:.3f}$,", "layout rates")
    expect(lay["equivalent_at_5"] and not lay["equivalent_at_5_unpaired"],
           "layout verdicts changed (paired equivalent, unpaired not)", errs)
    has(f"all ${lay['n_pairs']}$ object-layout variants", "layout variant count")
    cc = json.load(open(D / "fusion_shift.json"))["camera_confirmatory"]
    cam = rows["pi05_camera_confirmatory"]
    expect((cam["a_only"], cam["b_only"], cam["n_pairs"]) == (cc["s1_only"], cc["s10_only"], cc["pairs"]),
           "camera re-analysis disagrees with the camera-sample counts", errs)
    expect(cam["ci_pts"][1] < 0, "camera paired interval no longer excludes zero", errs)
    has(f"${cc['sr_s1']:.4f}$ vs.\\ ${cc['sr_s10']:.4f}$", "camera rates")
    has(f"${cc['s1_only']}$--${cc['s10_only']}$ discordant pairs", "camera discordants")
    has(f"${cc['pairs']}$ pairs", "camera pairs")
    expect(cc["mcnemar_p"] < 0.001 and max(cc["sr_s1"], cc["sr_s10"]) < 0.5,
           "camera p or failure-majority statement no longer holds", errs)
    has("p{=}0.0008", "camera p")

    # --- variance note in Sec. IV ---
    v1 = json.load(open(D / "v1_varcomp_report.json"))
    t8 = v1["tasks"]["libero_10/task8"]
    tot = t8["var_init"] + t8["e_pq_sampling"]
    has(f"task 8 carries total outcome variance ${tot:.3f}$", "task8 total variance")

    # --- Sec. audit ---
    aud = json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))
    has(f"${aud['n_comparisons']}$ highlighted comparisons from 50 VLA papers, "
        f"${100 * aud['unusable_rate']:.1f}\\%$ state no usable rollout count", "unusable n")
    ex = [json.loads(line) for line in open(ROOT / "docs/audit/extraction.jsonl")]
    seeds = sum(1 for r in ex for c in r["comparisons"] if c["seeds_stated"])
    has(f"evaluation-seed counts appear for ${seeds}$", "seed reporting")
    unc = 100 * aud["share_not_significant"]
    h = json.load(open(D / "audit_holm.json"))
    expect(abs(h["uncorrected_pct"] - unc) < 0.05, "audit_holm.json stale", errs)
    has(f"${unc:.1f}\\%$ fail an exact test", "audit failure rate")

    # --- corpus size ---
    n_ep = sum(1 for f in (ROOT / "artifact").rglob("records_*.jsonl") for line in open(f) if line.strip())
    has(f"${n_ep:,}$ released episode records".replace(",", "{,}"), "episode count")

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
