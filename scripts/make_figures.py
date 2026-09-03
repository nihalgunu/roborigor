"""Paper figures, regenerated from committed data by one command.

Print-first: single-hue sequential ramp for num_steps (magnitude), marker
shape for exec_horizon (secondary encoding), dark edges + direct labels
for low-ink relief, one axis per chart, no rainbow.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/paper-data"
OUT = ROOT / "paper/figures"
OUT.mkdir(parents=True, exist_ok=True)

NS_COLOR = {1: "#c6dbef", 2: "#6baed6", 5: "#2171b5", 10: "#08306b"}
EH_MARKER = {1: "^", 5: "s", 10: "o"}
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "ps.fonttype": 42})


def fig_hero():
    """Fig. 1: (a) where the variance lives, (b) what each factor moves."""
    import statistics
    import numpy as np
    from matplotlib.patches import Rectangle
    NAVY, LIGHT, MID, ACCENT, INK = "#08306b", "#6baed6", "#2171b5", "#8c510a", "#333333"

    # ---- panel (a): variance partition at fixed initial state ----
    dm = json.load(open(DATA / "decomp_minis.json"))
    v1t = json.load(open(DATA / "v1_varcomp_report.json"))["tasks"]["libero_10/task8"]
    pol = [("$\\pi_{0.5}$", v1t["icc"], v1t["mu"]),
           ("$\\pi_0$", dm["pi0_libero"]["icc"], dm["pi0_libero"]["mu"]),
           ("SmolVLA", dm["smolvla_libero"]["icc"], dm["smolvla_libero"]["mu"])]

    # ---- panel (b): ranked movers ----
    cell = {(c["num_steps"], c["exec_horizon"]): c["success_rate"]
            for c in json.load(open(DATA / "v2_knob_table.json"))["cells"]}
    horizon_cost = (cell[(1, 10)] - cell[(1, 1)]) * 100.0
    denoise_delta = (cell[(1, 10)] - cell[(10, 10)]) * 100.0
    pilot = json.load(open(DATA / "pilot_rank_analysis.json"))
    clean = pilot["clean_reference"]["pi05"] * 100.0
    camera_drop = clean - pilot["axis_results"]["Camera Viewpoints"]["pert"]["pi05"] * 100.0
    layout_drop = clean - pilot["axis_results"]["Objects Layout"]["pert"]["pi05"] * 100.0
    axes_j = json.load(open(DATA / "new_axes.json"))["axes"]
    def pooled_drop(axis):
        lv = axes_j[axis]["pi05_libero"]
        return clean - 100.0 * sum(v["k"] for v in lv.values()) / sum(v["n"] for v in lv.values())
    light_drop, robot_drop = pooled_drop("Light Conditions"), pooled_drop("Robot Initial States")
    reseed = json.load(open(DATA / "reseed_std_protocol.json"))
    seed_spread = reseed["spread_max_minus_min"]
    battery = json.load(open(DATA / "v1_varcomp_report.json"))["protocol_spread"]["max_minus_min_points"]
    audit = json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))
    gaps = sorted(abs(c["gap_points"]) for c in audit["comparisons"] if c["gap_points"] is not None)
    median_gap = statistics.median(gaps)
    n_comp = len(gaps)

    rows = [("Camera viewpoint", camera_drop, "shift"),
            ("Replan every step ($s{=}1$)", horizon_cost, "dial"),
            ("Robot initial state", robot_drop, "shift"),
            ("Object layout", layout_drop, "shift"),
            ("Lighting", light_drop, "shift"),
            ("Sampling seed", seed_spread, "dial"),
            ("Denoising steps 10$\\to$1", denoise_delta, "dial")]
    rows.sort(key=lambda r: -r[1])

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(3.5, 4.05), dpi=300,
                                   gridspec_kw={"height_ratios": [1.0, 1.45]})
    fig.subplots_adjust(left=0.30, right=0.97, top=0.90, bottom=0.10, hspace=0.62)

    nd = json.load(open(DATA / "nondeterminism.json"))["informative_task"]
    ys = np.arange(len(pol))[::-1]
    for y, (name, icc, mu) in zip(ys, pol):
        within = 100 * (1 - icc)
        # the replicate block measures the sampler/system split on pi0.5 only
        if name.startswith("$\\pi_{0.5}$"):
            samp, sysnd = nd["pct_sampler_net"], nd["pct_nondeterminism"]
            axA.barh(y, samp, height=0.55, color=NAVY, zorder=3)
            axA.barh(y, sysnd, left=samp, height=0.55, color=MID, zorder=3)
            axA.text(samp / 2, y, f"{samp:.0f}%", va="center", ha="center",
                     fontsize=7, color="white", zorder=5)
            axA.text(samp + sysnd / 2, y, f"{sysnd:.0f}%", va="center", ha="center",
                     fontsize=7, color="white", zorder=5)
        else:
            axA.barh(y, within, height=0.55, color=NAVY, zorder=3,
                     hatch="//", edgecolor="white", linewidth=0)
            axA.text(within / 2, y, f"{within:.0f}%", va="center", ha="center",
                     fontsize=7, color="white", zorder=5,
                     bbox={"facecolor": NAVY, "edgecolor": "none", "pad": 1.0})
        axA.barh(y, 100 - within, left=within, height=0.55, color=LIGHT, zorder=3)
        axA.text(101, y, f"base rate {mu:.2f}", va="center", ha="left",
                 fontsize=6, color=INK)
    axA.set_yticks(ys); axA.set_yticklabels([p[0] for p in pol], fontsize=7)
    axA.tick_params(axis="y", length=0); axA.set_xlim(0, 100); axA.set_ylim(-0.6, len(pol) - 0.4)
    axA.set_xticks([0, 25, 50, 75, 100]); axA.tick_params(axis="x", labelsize=6.5)
    axA.set_xlabel("share of outcome variance at a fixed initial state (%)", fontsize=7, labelpad=2)
    axA.set_title("(a) what survives fixing the scene", fontsize=7.5, pad=28)
    for x, col, lab in ((0.02, NAVY, "flow sampler"),
                        (0.36, MID, "system nondet."),
                        (0.74, LIGHT, "initial state")):
        axA.add_patch(Rectangle((x, 1.135), 0.030, 0.070, transform=axA.transAxes,
                                facecolor=col, edgecolor="none", clip_on=False))
        axA.text(x + 0.038, 1.168, lab, transform=axA.transAxes, fontsize=6.5,
                 va="center", color=INK)
    axA.add_patch(Rectangle((0.02, 1.035), 0.030, 0.070, transform=axA.transAxes,
                            facecolor=NAVY, edgecolor="white", hatch="//",
                            linewidth=0, clip_on=False))
    axA.text(0.058, 1.068, "sampler + system (split not measured)",
             transform=axA.transAxes, fontsize=6.5, va="center", color=INK)

    ys2 = np.arange(len(rows))[::-1]
    BOX = dict(facecolor="white", edgecolor="none", pad=0.5)
    for y, (label, val, grp) in zip(ys2, rows):
        axB.barh(y, val, height=0.6, color=(NAVY if grp == "dial" else MID), zorder=3)
        if label == "Sampling seed":
            axB.barh(y, battery - val, left=val, height=0.6, facecolor="none",
                     edgecolor=NAVY, hatch="/////", linewidth=0.6, zorder=3)
            axB.text(battery + 0.8, y, f"{val:.1f} ({battery:.1f} on battery)",
                     va="center", ha="left", fontsize=6.5, color=INK, zorder=5, bbox=BOX)
        else:
            axB.text(val + 0.8, y, f"{val:.1f}", va="center", ha="left",
                     fontsize=6.8, color=INK, zorder=5, bbox=BOX)
    axB.set_yticks(ys2); axB.set_yticklabels([r[0] for r in rows], fontsize=6.8)
    axB.tick_params(axis="y", length=0); axB.set_ylim(-0.6, len(rows) - 0.4); axB.set_xlim(0, 52)
    axB.set_xticks([0, 10, 20, 30, 40]); axB.tick_params(axis="x", labelsize=6.5)
    axB.set_xlabel("points moved on $\\pi_{0.5}$ success rate", fontsize=7, labelpad=2)
    axB.axvline(median_gap, color=ACCENT, linestyle=(0, (4, 2.5)), linewidth=1.0, zorder=4)
    axB.annotate(f"median claimed gain,\n{n_comp} audited comparisons: {median_gap:.1f}",
                 xy=(median_gap + 0.3, 0.55), xytext=(15.5, 0.15), fontsize=6.2, color=ACCENT,
                 ha="left", va="center", linespacing=1.25,
                 arrowprops=dict(arrowstyle="-", color=ACCENT, linewidth=0.7,
                                 shrinkA=2, shrinkB=1, connectionstyle="arc3,rad=-0.18"), zorder=6)
    axB.set_title("(b) what each factor moves", fontsize=7.5, pad=4)
    for a in (axA, axB):
        a.xaxis.grid(True, color="#dddddd", linewidth=0.5, zorder=0); a.set_axisbelow(True)
    fig.savefig(OUT / "fig_hero.pdf", bbox_inches="tight")
    print("fig_hero.pdf (decomposition + movers)")


def fig_hero_old():
    """Fig. 1: ranked movers of the pi0.5 success rate vs the field's median claim."""
    import statistics
    from matplotlib.patches import Rectangle
    NAVY, LIGHT, ACCENT, INK = "#08306b", "#6baed6", "#8c510a", "#333333"
    cell = {(c["num_steps"], c["exec_horizon"]): c["success_rate"]
            for c in json.load(open(DATA / "v2_knob_table.json"))["cells"]}
    horizon_cost = (cell[(1, 10)] - cell[(1, 1)]) * 100.0
    denoise_delta = (cell[(1, 10)] - cell[(10, 10)]) * 100.0
    pilot = json.load(open(DATA / "pilot_rank_analysis.json"))
    clean = pilot["clean_reference"]["pi05"] * 100.0
    camera_drop = clean - pilot["axis_results"]["Camera Viewpoints"]["pert"]["pi05"] * 100.0
    layout_drop = clean - pilot["axis_results"]["Objects Layout"]["pert"]["pi05"] * 100.0
    axes_j = json.load(open(DATA / "new_axes.json"))["axes"]
    def pooled_drop(axis):
        lv = axes_j[axis]["pi05_libero"]
        return clean - 100.0 * sum(v["k"] for v in lv.values()) / sum(v["n"] for v in lv.values())
    light_drop, robot_drop = pooled_drop("Light Conditions"), pooled_drop("Robot Initial States")
    reseed = json.load(open(DATA / "reseed_std_protocol.json"))
    seed_spread = reseed["spread_max_minus_min"]
    battery_spread = json.load(open(DATA / "v1_varcomp_report.json"))["protocol_spread"]["max_minus_min_points"]
    audit = json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))
    gaps = sorted(abs(c["gap_points"]) for c in audit["comparisons"] if c["gap_points"] is not None)
    median_gap = statistics.median(gaps)
    n_comp = len(gaps)
    share_in_band = round(100 * sum(1 for g in gaps if abs(g) <= seed_spread) / n_comp)

    rows = [
        ("Camera viewpoint shift", camera_drop, "shift", f"$-${camera_drop:.1f}"),
        ("Replan every step\n(horizon 10$\\to$1, $s{=}1$)", horizon_cost, "dial", f"$-${horizon_cost:.1f}"),
        ("Robot initial-state shift", robot_drop, "shift", f"$-${robot_drop:.1f}"),
        ("Object layout shift", layout_drop, "shift", f"$-${layout_drop:.1f}"),
        ("Lighting shift", light_drop, "shift", f"$-${light_drop:.1f}"),
        ("Sampling seed\n(10 reseeds)", seed_spread, "dial", f"$\\pm${seed_spread:.1f}"),
        ("Denoising steps\n10$\\to$1 (h=10)", denoise_delta, "dial", f"$+${denoise_delta:.1f}"),
    ]
    rows.sort(key=lambda r: r[1], reverse=True)
    fig, ax = plt.subplots(figsize=(3.5, 2.7), dpi=300)
    fig.subplots_adjust(left=0.335, right=0.985, top=0.86, bottom=0.2)
    LBL_BBOX = dict(facecolor="white", edgecolor="none", pad=0.6)
    n = len(rows)
    ys = list(range(n - 1, -1, -1))
    for (label, val, grp, vtxt), y in zip(rows, ys):
        color = NAVY if grp == "dial" else LIGHT
        ax.barh(y, val, height=0.62, color=color, zorder=3)
        if label.startswith("Sampling seed"):
            ax.barh(y, battery_spread - val, left=val, height=0.62,
                    facecolor="none", edgecolor=NAVY, hatch="/////",
                    linewidth=0.6, zorder=3)
            ax.text(battery_spread + 0.7, y,
                    f"{vtxt}  ($\\pm${battery_spread:.1f} across battery)",
                    va="center", ha="left", fontsize=7, color=INK, zorder=5, bbox=LBL_BBOX)
        else:
            ax.text(val + 0.7, y, vtxt, va="center", ha="left",
                    fontsize=7.5, color=INK, zorder=5, bbox=LBL_BBOX)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0].replace("\\n", "\n") for r in rows], fontsize=7)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.55, n - 0.42)
    ax.set_xlim(0, 50)
    ax.set_xticks([0, 10, 20, 30, 40])
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("points moved on $\\pi_{0.5}$ success rate", fontsize=7.5, labelpad=2)
    ax.xaxis.grid(True, color="#dddddd", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.axvline(median_gap, color=ACCENT, linestyle=(0, (4, 2.5)), linewidth=1.0, zorder=4)
    ax.annotate(
        f"median claimed improvement in\n{n_comp} audited comparisons: {median_gap:.1f} pts\n"
        f"({share_in_band}% are within seed noise)",
        xy=(median_gap + 0.3, 0.60), xytext=(15.0, 0.05),
        fontsize=6.6, color=ACCENT, ha="left", va="center", linespacing=1.25,
        arrowprops=dict(arrowstyle="-", color=ACCENT, linewidth=0.7,
                        shrinkA=2, shrinkB=1, connectionstyle="arc3,rad=-0.18"),
        zorder=6)
    def key_swatch(x, color, text):
        ax.add_patch(Rectangle((x, 1.045), 0.030, 0.055, transform=ax.transAxes,
                               facecolor=color, edgecolor="none", clip_on=False))
        ax.text(x + 0.042, 1.072, text, transform=ax.transAxes,
                fontsize=7, va="center", ha="left", color=INK)
    key_swatch(0.03, NAVY, "inference dial you set")
    key_swatch(0.56, LIGHT, "deployment shift")
    fig.savefig(OUT / "fig_hero.pdf", bbox_inches="tight")
    print("fig_hero.pdf (movers, tournament winner)")


def fig_pareto():
    t = json.load(open(DATA / "v2_knob_table.json"))
    fig, ax = plt.subplots(figsize=(3.5, 2.5), dpi=300)
    frontier = {(c["num_steps"], c["exec_horizon"]) for c in t["pareto_frontier"]}
    label_cells = frontier | {(10, 5), (1, 1), (10, 1), (10, 10)}
    fx, fy = [], []
    for c in sorted(t["cells"], key=lambda c: c["measured_latency_ms_per_step"]):
        x, y = c["measured_latency_ms_per_step"], c["success_rate"]
        lo, hi = c["ci95"]
        key = (c["num_steps"], c["exec_horizon"])
        on_f = key in frontier
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="none",
                    ecolor="#999999", elinewidth=0.8, capsize=1.5, zorder=1)
        ax.scatter(x, y, s=48 if on_f else 30,
                   c=NS_COLOR[c["num_steps"]], marker=EH_MARKER[c["exec_horizon"]],
                   edgecolors="#1a1a1a", linewidths=0.7, zorder=3)
        if on_f:
            fx.append(x)
            fy.append(y)
        if key in label_cells:
            va = (0, -11) if key in {(1, 1), (10, 5)} else (4, 6)
            weight = "bold" if on_f or key == (10, 5) else "normal"
            ax.annotate(f"({key[0]},{key[1]})", (x, y), textcoords="offset points",
                        xytext=va, fontsize=6, color="#1a1a1a", fontweight=weight)
    if len(fx) > 1:
        ax.plot(fx, fy, color="#1a1a1a", lw=0.8, ls="--", zorder=2)
    ax.set_xscale("log")
    ax.set_xticks([5, 10, 20, 40, 80])
    ax.set_xticklabels(["5", "10", "20", "40", "80"])
    ax.minorticks_off()
    ax.set_xlabel("Measured inference latency per step (ms, log)")
    ax.set_ylabel("Success rate")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_pareto.pdf", bbox_inches="tight")
    print("fig_pareto.pdf")


def fig_seed_spread():
    r = json.load(open(DATA / "reseed_std_protocol.json"))
    rates = list(r["rates_pct"].values())
    fig, ax = plt.subplots(figsize=(3.5, 1.6), dpi=300)
    ax.scatter(rates, [0] * len(rates), s=42, c="#2171b5",
               edgecolors="#1a1a1a", linewidths=0.7, zorder=3)
    lo, hi = min(rates), max(rates)
    ax.annotate("", xy=(hi, 0.5), xytext=(lo, 0.5),
                arrowprops={"arrowstyle": "<->", "color": "#1a1a1a", "lw": 0.9})
    ax.text((lo + hi) / 2, 0.66, f"seed spread {hi - lo:.1f} pts (SD {r['sd']})",
            ha="center", fontsize=7)
    ax.text((lo + hi) / 2, -0.8,
            "27% of audited claimed gaps fit inside this spread",
            ha="center", fontsize=7, color="#8c510a")
    ax.set_ylim(-1.1, 1.05)
    ax.set_xlim(lo - 0.5, hi + 0.5)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Headline success rate (%), standard 500-episode protocol")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_seed_spread.pdf", bbox_inches="tight")
    print("fig_seed_spread.pdf")


def fig_varstacks():
    r = json.load(open(DATA / "v1_varcomp_report.json"))
    tasks = sorted((t for t in r["tasks"].values() if "error" not in t),
                   key=lambda t: t["task_id"])
    fig, ax = plt.subplots(figsize=(3.5, 2.4), dpi=300)
    sat_x, labeled = [], False
    for x, t in enumerate(tasks):
        sat = t["sr_observed"] >= 0.96
        if sat:
            sat_x.append(x)
        c_init, c_samp = ("#d9d9d9", "#d9d9d9") if sat else ("#2171b5", "#c6dbef")
        lab = not sat and not labeled
        ax.bar(x, t["var_init"], color=c_init, edgecolor="#1a1a1a", linewidth=0.5,
               label="Initial state" if lab else None)
        ax.bar(x, t["e_pq_sampling"], bottom=t["var_init"], color=c_samp,
               edgecolor="#1a1a1a", linewidth=0.5,
               label="Within-init (sampler + system)" if lab else None)
        labeled = labeled or lab
    if sat_x:
        ymax = max(t["var_init"] + t["e_pq_sampling"] for t in tasks)
        sat_top = max(tasks[x]["var_init"] + tasks[x]["e_pq_sampling"] for x in sat_x)
        ax.text((min(sat_x) + max(sat_x)) / 2, sat_top + 0.04 * ymax, "saturated",
                ha="center", fontsize=6, color="#767676", style="italic")
    ax.set_xticks(range(len(tasks)))
    ax.set_xticklabels([f"t{t['task_id']}" for t in tasks])
    ax.set_ylabel("Outcome variance")
    ax.legend(loc="upper right", fontsize=6, framealpha=0.9, edgecolor="none")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_varstacks.pdf", bbox_inches="tight")
    print("fig_varstacks.pdf")


def fig_perturb():
    r = json.load(open(DATA / "pilot_rank_analysis.json"))
    clean = r["clean_reference"]
    styles = {
        "pi05": ("#08306b", "o", "$\\pi_{0.5}$", 4),
        "pi0": ("#2171b5", "s", "$\\pi_0$", -4),
        "smolvla": ("#6baed6", "^", "SmolVLA", -2),
    }
    panels = [("Camera Viewpoints", "Camera"), ("Objects Layout", "Objects Layout")]
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.4), dpi=300, sharey=True)
    for ax, (axis_key, title) in zip(axes, panels):
        pert = r["axis_results"][axis_key]["pert"]
        for pol, (color, marker, label, dy) in styles.items():
            ax.plot([0, 1], [clean[pol], pert[pol]], color=color, lw=1.2, zorder=2)
            ax.scatter([0, 1], [clean[pol], pert[pol]], s=30, c=color, marker=marker,
                       edgecolors="#1a1a1a", linewidths=0.7, zorder=3)
            ax.annotate(label, (0, clean[pol]), textcoords="offset points",
                        xytext=(-4, dy), ha="right", va="center",
                        fontsize=6, color="#1a1a1a")
        ax.set_title(title, fontsize=7)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["clean", "perturbed"])
        ax.set_xlim(-0.45, 1.15)
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("Success rate")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_perturb.pdf", bbox_inches="tight")
    print("fig_perturb.pdf")


def fig_newaxes():
    r = json.load(open(DATA / "new_axes.json"))["axes"]
    styles = {
        "pi05_libero": ("#08306b", "o", "$\\pi_{0.5}$"),
        "pi0_libero": ("#2171b5", "s", "$\\pi_0$"),
        "smolvla_libero": ("#6baed6", "^", "SmolVLA"),
    }
    panels = [("Light Conditions", "Light Conditions"),
              ("Robot Initial States", "Robot Initial States")]
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.2), dpi=300, sharey=True)
    for ax, (key, title) in zip(axes, panels):
        for pol, (color, marker, label) in styles.items():
            if pol not in r.get(key, {}):
                continue
            lv = sorted(r[key][pol], key=int)
            xs = [int(l) for l in lv]
            ys = [r[key][pol][l]["sr"] for l in lv]
            los = [ys[i] - r[key][pol][l]["cp"][0] for i, l in enumerate(lv)]
            his = [r[key][pol][l]["cp"][1] - ys[i] for i, l in enumerate(lv)]
            ax.errorbar(xs, ys, yerr=[los, his], color=color, lw=1.2,
                        marker=marker, ms=3.5, mec="#1a1a1a", mew=0.5,
                        elinewidth=0.6, capsize=1.5, zorder=3)
            ax.annotate(label, (xs[-1], ys[-1]), textcoords="offset points",
                        xytext=(3, 0), ha="left", va="center",
                        fontsize=6, color="#1a1a1a")
        ax.set_title(title, fontsize=7)
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.set_xlim(0.6, 6.1)
        ax.set_ylim(-0.02, 1.05)
        ax.set_xlabel("Perturbation level")
    axes[0].set_ylabel("Success rate")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_newaxes.pdf", bbox_inches="tight")
    print("fig_newaxes.pdf")


def fig_audit():
    r = json.load(open(ROOT / "docs/audit/recompute_final_50papers.json"))
    rows = [c for c in r["comparisons"] if c["mde_points"] is not None]
    fig, ax = plt.subplots(figsize=(3.5, 2.4), dpi=300)
    ax.plot([0.07, 80], [0.07, 80], color="#1a1a1a", lw=0.8, ls="--", zorder=2)
    for sig, color, label in [(True, "#2171b5", "significant at stated n"),
                              (False, "#8c510a", "not significant")]:
        xs = [c["mde_points"] for c in rows if c["significant_05"] == sig]
        ys = [abs(c["gap_points"]) for c in rows if c["significant_05"] == sig]
        ax.scatter(xs, ys, s=22, c=color, edgecolors="#1a1a1a", linewidths=0.5,
                   zorder=3, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.9, 50)
    ax.set_ylim(0.07, 80)
    ax.set_xticks([1, 2, 5, 10, 20, 40])
    ax.set_xticklabels(["1", "2", "5", "10", "20", "40"])
    ax.set_yticks([0.1, 1, 5, 20, 50])
    ax.set_yticklabels(["0.1", "1", "5", "20", "50"])
    ax.minorticks_off()
    ax.text(35, 0.12, "gap < its own MDE", ha="right", fontsize=6, color="#777777")
    ax.text(1.05, 45, "detectable", ha="left", fontsize=6, color="#777777")
    ax.legend(fontsize=6, frameon=False, loc="lower left", handletextpad=0.3)
    ax.set_xlabel("Protocol MDE (points, 80% power)")
    ax.set_ylabel("|Highlighted gap| (points)")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_audit.pdf", bbox_inches="tight")
    print("fig_audit.pdf")


if __name__ == "__main__":
    fig_hero()
    fig_pareto()
    fig_seed_spread()
    fig_varstacks()
    fig_perturb()
    fig_newaxes()
    fig_audit()
