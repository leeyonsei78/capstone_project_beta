"""
Reliance sensitivity analysis (improvement 5): what the human+advisor team achieves for a *range* of
assumed reviewer reliance, without running a human-subject study.

Model (stated assumptions, not measurements)
  * The advisor outputs flag or clean. With probability r_flag the reviewer adopts a "flag", with
    probability r_clean the reviewer adopts a "clean"; otherwise the reviewer decides alone.
  * A reviewer deciding alone flags an anomalous case with probability hum_sens and a legitimate case
    with probability 1 - hum_spec.
  * Advisor and reviewer errors are independent given the true class. (Real errors are correlated and
    reviewers anchor on the advice; independence is the optimistic assumption.)
  * Asymmetric reliance (r_clean > r_flag) models automation bias: trusting a "clean" more than a "flag".

hum_sens / hum_spec are PLACEHOLDERS for the domain expert to replace with company figures; adv_sens and
adv_spec come from the measured advisor results. The output is a sensitivity table, not evidence about
real reviewers, and the paper must say so (see related_work_notes.md on automation bias).
"""


def team(adv_sens, adv_spec, hum_sens, hum_spec, r_flag, r_clean, prevalence=0.03):
    # anomalous case
    flag_anom = adv_sens * (r_flag + (1 - r_flag) * hum_sens) + (1 - adv_sens) * ((1 - r_clean) * hum_sens)
    # legitimate case
    flag_legit = (1 - adv_spec) * (r_flag + (1 - r_flag) * (1 - hum_spec)) + adv_spec * ((1 - r_clean) * (1 - hum_spec))
    tp = prevalence * flag_anom
    fp = (1 - prevalence) * flag_legit
    return {
        "team_sens": flag_anom, "team_spec": 1 - flag_legit,
        "delta_sens_vs_human": flag_anom - hum_sens, "delta_spec_vs_human": (1 - flag_legit) - hum_spec,
        "ppv": tp / (tp + fp) if (tp + fp) else None,
        "missed_per_1000": 1000 * prevalence * (1 - flag_anom),
        "false_holds_per_1000": 1000 * (1 - prevalence) * flag_legit,
    }


def table(adv_sens, adv_spec, hum_sens, hum_spec, prevalence=0.03,
          reliances=(0.0, 0.25, 0.5, 0.75, 1.0), asym_clean=0.9):
    """Rows for symmetric reliance r (r_flag = r_clean = r) plus one automation-bias row per r
    (r_clean = max(r, asym_clean), r_flag = r)."""
    rows = []
    for r in reliances:
        sym = team(adv_sens, adv_spec, hum_sens, hum_spec, r, r, prevalence)
        bias = team(adv_sens, adv_spec, hum_sens, hum_spec, r, max(r, asym_clean), prevalence)
        rows.append({"reliance": r, "symmetric": sym, "automation_bias": bias})
    return rows


def render_markdown(adv_sens, adv_spec, hum_sens, hum_spec, prevalence=0.03):
    out = [f"> Placeholders: human sens={hum_sens}, spec={hum_spec}, prevalence={prevalence}. "
           f"Advisor (measured): sens={adv_sens:.3f}, spec={adv_spec:.3f}. Independence assumed.", "",
           "| reliance r | team sens | team spec | missed / 1000 | false holds / 1000 | "
           "missed / 1000 (auto. bias) |", "|---|---|---|---|---|---|"]
    for row in table(adv_sens, adv_spec, hum_sens, hum_spec, prevalence):
        s, b = row["symmetric"], row["automation_bias"]
        out.append(f"| {row['reliance']:.2f} | {s['team_sens']:.3f} | {s['team_spec']:.3f} | "
                   f"{s['missed_per_1000']:.1f} | {s['false_holds_per_1000']:.1f} | {b['missed_per_1000']:.1f} |")
    return "\n".join(out) + "\n"
