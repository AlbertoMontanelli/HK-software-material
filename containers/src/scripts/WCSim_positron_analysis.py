#!/usr/bin/env python3
"""
Analyze compact positron ROOT summaries.

Input ROOT file must contain:
    - EventSummary
    - PmtHitMap
    - Geometry

Outputs:
    - histograms per generated energy
    - 3D Plotly detector displays for representative events
    - 2D PMT charge maps for representative events

Representative events are chosen, for each energy, among events with valid
digitized hits, using the 10%, 50%, 90%, and 100% quantiles of total charge.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go  # type: ignore
import ROOT  # type: ignore

OUTPUT_DIR = Path("/plots/positron")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_label(label):
    return str(label).replace(".", "p").replace("-", "m").replace("+", "p")


def energy_display_label(energy_MeV):
    """
    Human-readable energy label.

    Examples:
        0.3  -> '0.3 MeV'
        1.0  -> '1 MeV'
        10.0 -> '10 MeV'
    """
    energy = float(energy_MeV)

    if np.isclose(energy, round(energy)):
        return f"{int(round(energy))} MeV"

    return f"{energy:g} MeV"


def energy_file_label(energy_MeV):
    """
    File/directory-safe energy label.

    Examples:
        0.3  -> '0p300MeV'
        1.0  -> '1MeV'
        10.0 -> '10MeV'
    """
    energy = float(energy_MeV)

    if np.isclose(energy, round(energy)):
        return f"{int(round(energy))}MeV"

    return f"{energy:.3f}MeV".replace(".", "p")


def load_geometry(root_file):
    """
    Read compact Geometry tree.

    Returns
    -------
    pmt_map : dict
        tube_id -> {
            "x": x,
            "y": y,
            "z": z,
            "cyl_loc": cyl_loc,
        }
    """

    geo_tree = root_file.Get("Geometry")
    if not geo_tree:
        raise RuntimeError("Could not find tree 'Geometry' in input file.")

    if int(geo_tree.GetEntries()) < 1:
        raise RuntimeError("Geometry tree exists but has no entries.")

    geo_tree.GetEntry(0)

    pmt_map = {}

    tube_ids = list(geo_tree.tube_id)
    xs = list(geo_tree.x)
    ys = list(geo_tree.y)
    zs = list(geo_tree.z)

    if hasattr(geo_tree, "cyl_loc"):
        cyl_locs = list(geo_tree.cyl_loc)
    else:
        raise RuntimeError(
            "Geometry tree has no branch 'cyl_loc'. "
            "Regenerate the summary ROOT file with the updated "
            "WCSim_positron_summary.py."
        )

    for tube_id, x, y, z, cyl_loc in zip(tube_ids, xs, ys, zs, cyl_locs):
        pmt_map[int(tube_id)] = {
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "cyl_loc": int(cyl_loc),
        }

    return pmt_map


def build_event_rows(event_tree):
    """
    Read EventSummary and build a list of plain Python dictionaries.

    One row corresponds to one EventSummary entry.
    """

    rows = []

    n_entries = int(event_tree.GetEntries())

    for tree_entry in range(n_entries):
        event_tree.GetEntry(tree_entry)

        true_start = np.array(
            [
                float(event_tree.true_start[0]),
                float(event_tree.true_start[1]),
                float(event_tree.true_start[2]),
            ],
            dtype=float,
        )

        true_stop = np.array(
            [
                float(event_tree.true_stop[0]),
                float(event_tree.true_stop[1]),
                float(event_tree.true_stop[2]),
            ],
            dtype=float,
        )

        true_dir = np.array(
            [
                float(event_tree.true_dir[0]),
                float(event_tree.true_dir[1]),
                float(event_tree.true_dir[2]),
            ],
            dtype=float,
        )

        min_time = float(event_tree.min_time)
        max_time = float(event_tree.max_time)

        if np.isfinite(min_time) and np.isfinite(max_time):
            time_span = max_time - min_time
        else:
            time_span = np.nan

        row = {
            "tree_entry": int(tree_entry),
            "entry_index": int(event_tree.entry_index),
            "energy_MeV": float(event_tree.energy_MeV),
            "track_length_cm": float(event_tree.track_length_cm),
            "n_triggers": int(event_tree.n_triggers),
            "n_raw_hits": int(event_tree.n_raw_hits),
            "n_digi_hits": int(event_tree.n_digi_hits),
            "n_raw_tubes_hit_sum": int(event_tree.n_raw_tubes_hit_sum),
            "n_digi_tubes_hit_sum": int(event_tree.n_digi_tubes_hit_sum),
            "n_digi_tubes_hit_merged": int(event_tree.n_digi_tubes_hit_merged),
            "tot_charge": float(event_tree.tot_charge),
            "min_time": float(min_time),
            "max_time": float(max_time),
            "time_span": time_span,
            "true_start": true_start,
            "true_stop": true_stop,
            "true_dir": true_dir,
            "true_p": float(event_tree.true_p),
            "true_E": float(event_tree.true_E),
            "true_K": float(event_tree.true_K),
            "true_M": float(event_tree.true_M),
            "true_time": float(event_tree.true_time),
            "true_ipnu": int(event_tree.true_ipnu),
            "true_parent_type": int(event_tree.true_parent_type),
        }

        rows.append(row)

    return rows


def save_histogram(rows, key, xlabel, title, output_path):
    values = np.array(
        [row[key] for row in rows if np.isfinite(row[key])],
        dtype=float,
    )

    if len(values) == 0:
        return False

    integer_keys = {
        "n_triggers",
        "n_raw_hits",
        "n_digi_hits",
        "n_raw_tubes_hit_sum",
        "n_digi_tubes_hit_sum",
        "n_digi_tubes_hit_merged",
    }

    plt.figure(figsize=(8, 6))

    if key in integer_keys:
        values_int = values.astype(int)

        unique_values, counts = np.unique(values_int, return_counts=True)

        plt.bar(
            unique_values,
            counts,
            width=1.0,
            align="center",
            edgecolor="black",
            linewidth=0.5,
        )

        plt.ylabel("Events", fontsize=14)

    else:
        plt.hist(values, bins="fd", histtype="step", linewidth=1.8)
        plt.ylabel("Events", fontsize=14)

    plt.xlabel(xlabel, fontsize=14)
    plt.title(title, fontsize=14)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return True


def save_histograms_for_energy(rows, energy_label, output_dir):

    variables = [
        ("track_length_cm", "positron track length [cm]"),
        ("n_raw_hits", "number of raw Cherenkov hits"),
        ("n_digi_hits", "number of digitized hits"),
        ("time_span", r"$t_{\max} - t_{\min}$ [ns]"),
        ("n_raw_tubes_hit_sum", "number of raw tubes hit, trigger-summed"),
        ("n_digi_tubes_hit_sum", "number of digitized tubes hit, trigger-summed"),
        ("n_digi_tubes_hit_merged", "number of digitized tubes hit, merged"),
        ("tot_charge", "total collected charge [p.e.]"),
    ]

    for key, xlabel in variables:
        output_path = output_dir / f"{key}.png"
        title = f"{energy_label}: {xlabel}"
        save_histogram(rows, key, xlabel, title, output_path)


def has_valid_digihits(row):
    return (
        row["n_digi_hits"] > 0
        and row["n_digi_tubes_hit_merged"] > 0
        and np.isfinite(float(row["tot_charge"]))
        and float(row["tot_charge"]) > 0
    )


def select_representative_events(rows):
    """
    Select representative events using total charge quantiles.

    Quantiles:
        - 10%
        - 50%
        - 90%
        - 100%

    Only events with valid digitized hits are considered.
    """

    valid = [row for row in rows if has_valid_digihits(row)]

    if len(valid) == 0:
        return []

    charges = np.array([row["tot_charge"] for row in valid], dtype=float)
    quantiles = [0.10, 0.50, 0.90, 1.00]

    selected = []
    selected_entry_indices = set()

    for q in quantiles:
        target = float(np.quantile(charges, q))

        best = min(
            valid,
            key=lambda row: abs(float(row["tot_charge"]) - target),
        )

        if best["entry_index"] not in selected_entry_indices:
            selected.append(best)
            selected_entry_indices.add(best["entry_index"])

    # If two quantiles picked the same event, supplement with the highest-charge
    # remaining events until we reach at most four selected events.
    if len(selected) < min(4, len(valid)):
        remaining = [
            row
            for row in sorted(valid, key=lambda r: r["tot_charge"], reverse=True)
            if row["entry_index"] not in selected_entry_indices
        ]

        for row in remaining:
            selected.append(row)
            selected_entry_indices.add(row["entry_index"])

            if len(selected) >= min(4, len(valid)):
                break

    return selected


def read_hit_map_for_row(hit_tree, row):
    """
    Read PmtHitMap entry corresponding to this row.

    This assumes PmtHitMap was filled with one entry per event in the same order
    as EventSummary, which is how the summary-maker script was designed.
    """

    tree_entry = int(row["tree_entry"])
    hit_tree.GetEntry(tree_entry)

    hit_entry_index = int(hit_tree.entry_index)

    if hit_entry_index != int(row["entry_index"]):
        raise RuntimeError(
            "EventSummary and PmtHitMap are not aligned: "
            f"EventSummary entry_index={row['entry_index']}, "
            f"PmtHitMap entry_index={hit_entry_index}, "
            f"tree_entry={tree_entry}."
        )

    tube_ids = np.array(list(hit_tree.tube_id), dtype=int)
    charges = np.array(list(hit_tree.charge), dtype=float)
    times = np.array(list(hit_tree.time), dtype=float)

    return tube_ids, charges, times


def add_direction_arrow_3d(
    fig, start, direction, detector_scale, name="true positron direction"
):
    """
    Add a visible direction arrow to a Plotly 3D figure.

    The arrow length is display-oriented, not the true physical track length.
    """

    start = np.asarray(start, dtype=float)
    direction = np.asarray(direction, dtype=float)

    norm = np.linalg.norm(direction)
    if (
        norm <= 0
        or not np.all(np.isfinite(start))
        or not np.all(np.isfinite(direction))
    ):
        return

    direction = direction / norm

    arrow_length = 0.25 * detector_scale
    end = start + arrow_length * direction

    fig.add_trace(
        go.Scatter3d(
            x=[start[0], end[0]],
            y=[start[1], end[1]],
            z=[start[2], end[2]],
            mode="lines",
            line=dict(width=4),
            name=name,
        )
    )

    # Cone tip.
    fig.add_trace(
        go.Cone(
            x=[end[0]],
            y=[end[1]],
            z=[end[2]],
            u=[direction[0]],
            v=[direction[1]],
            w=[direction[2]],
            sizemode="absolute",
            sizeref=0.05 * detector_scale,
            anchor="tip",
            showscale=False,
            name="arrow head",
        )
    )

    # Start point.
    fig.add_trace(
        go.Scatter3d(
            x=[start[0]],
            y=[start[1]],
            z=[start[2]],
            mode="markers",
            marker=dict(size=4),
            name="true start vertex",
        )
    )


def save_3d_display(row, hit_tree, pmt_map, output_path):
    """
    Save an interactive 3D Plotly event display.

    All PMTs are shown as a faint detector outline.
    Hit PMTs are colored by merged digitized charge.
    The true positron direction is shown as a display-scaled arrow.
    """

    tube_ids, charges, times = read_hit_map_for_row(hit_tree, row)

    if len(tube_ids) == 0:
        return False

    charge_by_tube = {
        int(tube_id): float(charge) for tube_id, charge in zip(tube_ids, charges)
    }

    time_by_tube = {int(tube_id): float(time) for tube_id, time in zip(tube_ids, times)}

    all_x, all_y, all_z = [], [], []
    hit_x, hit_y, hit_z, hit_q, hit_text = [], [], [], [], []

    for tube_id, pmt in pmt_map.items():
        x = float(pmt["x"])
        y = float(pmt["y"])
        z = float(pmt["z"])

        all_x.append(x)
        all_y.append(y)
        all_z.append(z)

        if tube_id in charge_by_tube:
            q = charge_by_tube[tube_id]
            t = time_by_tube[tube_id]

            hit_x.append(x)
            hit_y.append(y)
            hit_z.append(z)
            hit_q.append(q)

            hit_text.append(f"tube={tube_id}<br>q={q:.3f} p.e.<br>t={t:.3f} ns")

    all_x = np.asarray(all_x, dtype=float)
    all_y = np.asarray(all_y, dtype=float)
    all_z = np.asarray(all_z, dtype=float)

    hit_x = np.asarray(hit_x, dtype=float)
    hit_y = np.asarray(hit_y, dtype=float)
    hit_z = np.asarray(hit_z, dtype=float)
    hit_q = np.asarray(hit_q, dtype=float)

    if len(hit_q) == 0:
        return False

    detector_scale = float(
        max(
            np.max(all_x) - np.min(all_x),
            np.max(all_y) - np.min(all_y),
            np.max(all_z) - np.min(all_z),
        )
    )

    fig = go.Figure()

    # ---------- All PMTs: faint detector outline ----------
    fig.add_trace(
        go.Scatter3d(
            x=all_x,
            y=all_y,
            z=all_z,
            mode="markers",
            name="all PMTs",
            marker=dict(
                size=2,
                color="lightgray",
                opacity=0.15,
            ),
            hoverinfo="skip",
            showlegend=True,
        )
    )

    # ---------- Hit PMTs ----------
    fig.add_trace(
        go.Scatter3d(
            x=hit_x,
            y=hit_y,
            z=hit_z,
            mode="markers",
            name="hit PMTs",
            marker=dict(
                size=5,
                color=hit_q,
                colorscale="Plasma",
                colorbar=dict(title="Charge [p.e.]"),
                opacity=0.95,
            ),
            text=hit_text,
            hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        )
    )

    # ---------- True direction arrow ----------
    start = np.asarray(row["true_start"], dtype=float)
    direction = np.asarray(row["true_dir"], dtype=float)

    if (
        detector_scale > 0
        and np.all(np.isfinite(start))
        and np.all(np.isfinite(direction))
        and np.linalg.norm(direction) > 0
    ):
        direction = direction / np.linalg.norm(direction)

        arrow_length = 0.23 * detector_scale
        arrow_end = start + arrow_length * direction

        # Thinner shaft than before.
        fig.add_trace(
            go.Scatter3d(
                x=[start[0], arrow_end[0]],
                y=[start[1], arrow_end[1]],
                z=[start[2], arrow_end[2]],
                mode="lines",
                line=dict(
                    width=4,
                    color="red",
                ),
                name="true positron direction",
                showlegend=True,
            )
        )

        # More visible cone head.
        fig.add_trace(
            go.Cone(
                x=[arrow_end[0]],
                y=[arrow_end[1]],
                z=[arrow_end[2]],
                u=[direction[0]],
                v=[direction[1]],
                w=[direction[2]],
                sizemode="absolute",
                sizeref=0.10 * detector_scale,
                anchor="tip",
                colorscale=[[0, "red"], [1, "red"]],
                showscale=False,
                opacity=0.95,
                name="direction arrow head",
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter3d(
                x=[start[0]],
                y=[start[1]],
                z=[start[2]],
                mode="markers",
                marker=dict(
                    size=6,
                    color="purple",
                    opacity=0.95,
                ),
                name="true start vertex",
                showlegend=True,
            )
        )

    # ---------- Text formatting ----------
    track_length = row.get("track_length_cm", np.nan)
    if track_length is not None and np.isfinite(track_length):
        length_string = f"{track_length:.2f} cm"
    else:
        length_string = "nan"

    if "time_span" in row and np.isfinite(row["time_span"]):
        time_span_string = f"{row['time_span']:.1f} ns"
    elif np.isfinite(row["min_time"]) and np.isfinite(row["max_time"]):
        time_span_string = f"{row['max_time'] - row['min_time']:.1f} ns"
    else:
        time_span_string = "nan"

    info_text = (
        f"Energy: {energy_display_label(row['energy_MeV'])}<br>"
        f"Entry: {row['entry_index']}<br>"
        f"Track length: {length_string}<br>"
        f"Total charge: {row['tot_charge']:.2f} p.e.<br>"
        f"Digitized hits: {row['n_digi_hits']}<br>"
        f"Hit PMTs: {row['n_digi_tubes_hit_merged']}<br>"
        f"Hit-time span: {time_span_string}<br>"
        f"Trigger objects: {row['n_triggers']}"
    )

    # ---------- Layout ----------
    fig.update_layout(
        title=dict(
            text=f"3D PMT display - {energy_display_label(row['energy_MeV'])}",
            x=0.42,
            y=0.97,
        ),
        # Left side reserved for legend + info box.
        # Right side reserved for the scene + charge colorbar.
        scene=dict(
            domain=dict(
                x=[0.28, 0.86],
                y=[0.05, 0.95],
            ),
            xaxis=dict(
                title="x [cm]",
                showbackground=True,
            ),
            yaxis=dict(
                title="y [cm]",
                showbackground=True,
            ),
            zaxis=dict(
                title="z [cm]",
                showbackground=True,
            ),
            aspectmode="data",
        ),
        legend=dict(
            x=0.02,
            y=0.90,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.78)",
            bordercolor="rgba(0,0,0,0.25)",
            borderwidth=1,
            font=dict(size=14),
        ),
        annotations=[
            dict(
                text=info_text,
                x=0.02,
                y=0.58,
                xref="paper",
                yref="paper",
                showarrow=False,
                align="left",
                bgcolor="rgba(255,255,255,0.82)",
                bordercolor="black",
                borderwidth=1,
                font=dict(size=14),
            )
        ],
        width=950,
        height=650,
        margin=dict(l=10, r=90, b=10, t=55),
    )

    fig.write_html(str(output_path))

    return True


def save_2d_display(row, hit_tree, pmt_map, output_path):
    """
    Save a 2D PMT display with detector regions arranged vertically:

        top cap
        unwrapped barrel
        bottom cap

    Barrel:
        x-axis = phi = atan2(y, x) [rad]
        y-axis = z [cm]

    Caps:
        x-axis = real x [cm]
        y-axis = real y [cm]

    Color represents merged digitized charge per PMT.
    """

    tube_ids, charges, times = read_hit_map_for_row(hit_tree, row)

    if len(tube_ids) == 0:
        return False

    charge_by_tube = {
        int(tube_id): float(charge) for tube_id, charge in zip(tube_ids, charges)
    }

    # ------------------------------------------------------------------
    # Separate PMTs according to detector region
    # ------------------------------------------------------------------

    all_top_x, all_top_y = [], []
    hit_top_x, hit_top_y, hit_top_q = [], [], []

    all_barrel_phi, all_barrel_z = [], []
    hit_barrel_phi, hit_barrel_z, hit_barrel_q = [], [], []

    all_bottom_x, all_bottom_y = [], []
    hit_bottom_x, hit_bottom_y, hit_bottom_q = [], [], []

    for tube_id, pmt in pmt_map.items():
        x = float(pmt["x"])
        y = float(pmt["y"])
        z = float(pmt["z"])
        cyl_loc = int(pmt["cyl_loc"])

        is_hit = tube_id in charge_by_tube

        # Top cap
        if cyl_loc == 0:
            all_top_x.append(x)
            all_top_y.append(y)

            if is_hit:
                hit_top_x.append(x)
                hit_top_y.append(y)
                hit_top_q.append(charge_by_tube[tube_id])

        # Barrel
        elif cyl_loc == 1:
            phi = np.arctan2(y, x)

            all_barrel_phi.append(phi)
            all_barrel_z.append(z)

            if is_hit:
                hit_barrel_phi.append(phi)
                hit_barrel_z.append(z)
                hit_barrel_q.append(charge_by_tube[tube_id])

        # Bottom cap
        elif cyl_loc == 2:
            all_bottom_x.append(x)
            all_bottom_y.append(y)

            if is_hit:
                hit_bottom_x.append(x)
                hit_bottom_y.append(y)
                hit_bottom_q.append(charge_by_tube[tube_id])

    # ------------------------------------------------------------------
    # Convert lists to NumPy arrays
    # ------------------------------------------------------------------

    all_top_x = np.asarray(all_top_x, dtype=float)
    all_top_y = np.asarray(all_top_y, dtype=float)
    hit_top_x = np.asarray(hit_top_x, dtype=float)
    hit_top_y = np.asarray(hit_top_y, dtype=float)
    hit_top_q = np.asarray(hit_top_q, dtype=float)

    all_barrel_phi = np.asarray(all_barrel_phi, dtype=float)
    all_barrel_z = np.asarray(all_barrel_z, dtype=float)
    hit_barrel_phi = np.asarray(hit_barrel_phi, dtype=float)
    hit_barrel_z = np.asarray(hit_barrel_z, dtype=float)
    hit_barrel_q = np.asarray(hit_barrel_q, dtype=float)

    all_bottom_x = np.asarray(all_bottom_x, dtype=float)
    all_bottom_y = np.asarray(all_bottom_y, dtype=float)
    hit_bottom_x = np.asarray(hit_bottom_x, dtype=float)
    hit_bottom_y = np.asarray(hit_bottom_y, dtype=float)
    hit_bottom_q = np.asarray(hit_bottom_q, dtype=float)

    # ------------------------------------------------------------------
    # Common charge scale
    # ------------------------------------------------------------------

    all_hit_q = np.concatenate(
        [
            hit_top_q,
            hit_barrel_q,
            hit_bottom_q,
        ]
    )

    if len(all_hit_q) > 0:
        q_min = float(np.min(all_hit_q))
        q_max = float(np.max(all_hit_q))

        if np.isclose(q_min, q_max):
            q_min = 0.0
            q_max = q_max + 1.0
    else:
        q_min = 0.0
        q_max = 1.0

    # ------------------------------------------------------------------
    # Common cap limits
    #
    # Using the same limits for both caps ensures that:
    #   - they have the same physical scale;
    #   - their centres coincide;
    #   - their apparent sizes are identical.
    # ------------------------------------------------------------------

    cap_extents = []

    if len(all_top_x) > 0:
        cap_extents.extend(
            [
                np.max(np.abs(all_top_x)),
                np.max(np.abs(all_top_y)),
            ]
        )

    if len(all_bottom_x) > 0:
        cap_extents.extend(
            [
                np.max(np.abs(all_bottom_x)),
                np.max(np.abs(all_bottom_y)),
            ]
        )

    if cap_extents:
        cap_lim = 1.05 * max(cap_extents)
    else:
        cap_lim = 1.0

    # ------------------------------------------------------------------
    # Figure layout
    #
    # The left empty column counterbalances the colorbar column.
    # Therefore, the central plotting column is centred in the figure.
    # ------------------------------------------------------------------

    fig = plt.figure(figsize=(10, 13))

    gs = fig.add_gridspec(
        nrows=3,
        ncols=3,
        height_ratios=[1.15, 2.2, 1.15],
        width_ratios=[0.075, 1.0, 0.075],
        hspace=0.35,
        wspace=0.08,
    )

    # Empty left column, used only to balance the colorbar.
    ax_spacer = fig.add_subplot(gs[:, 0])
    ax_spacer.axis("off")

    # Main plotting axes.
    ax_top = fig.add_subplot(gs[0, 1])
    ax_barrel = fig.add_subplot(gs[1, 1])
    ax_bottom = fig.add_subplot(gs[2, 1])

    # Dedicated colorbar axis.
    cax = fig.add_subplot(gs[:, 2])

    sc = None

    # ------------------------------------------------------------------
    # Top cap
    # ------------------------------------------------------------------

    ax_top.scatter(
        all_top_x,
        all_top_y,
        s=5,
        c="lightgray",
        alpha=0.35,
        linewidths=0,
        label="all PMTs",
    )

    if len(hit_top_q) > 0:
        sc = ax_top.scatter(
            hit_top_x,
            hit_top_y,
            s=18,
            c=hit_top_q,
            cmap="plasma",
            vmin=q_min,
            vmax=q_max,
            linewidths=0,
            alpha=0.95,
            label="hit PMTs",
        )

    ax_top.set_title("Top cap", fontsize=14)
    ax_top.set_xlabel("x [cm]", fontsize=13)
    ax_top.set_ylabel("y [cm]", fontsize=13)

    ax_top.set_xlim(-cap_lim, cap_lim)
    ax_top.set_ylim(-cap_lim, cap_lim)

    ax_top.set_aspect("equal", adjustable="box")
    ax_top.set_box_aspect(1)

    ax_top.grid(alpha=0.25)
    ax_top.tick_params(axis="both", labelsize=14)

    # ------------------------------------------------------------------
    # Unwrapped barrel
    # ------------------------------------------------------------------

    ax_barrel.scatter(
        all_barrel_phi,
        all_barrel_z,
        s=5,
        c="lightgray",
        alpha=0.35,
        linewidths=0,
    )

    if len(hit_barrel_q) > 0:
        sc = ax_barrel.scatter(
            hit_barrel_phi,
            hit_barrel_z,
            s=18,
            c=hit_barrel_q,
            cmap="plasma",
            vmin=q_min,
            vmax=q_max,
            linewidths=0,
            alpha=0.95,
        )

    ax_barrel.set_title("Unwrapped barrel", fontsize=14)
    ax_barrel.set_xlabel(
        r"$\phi = \mathrm{atan2}(y,x)$ [rad]",
        fontsize=13,
    )
    ax_barrel.set_ylabel("z [cm]", fontsize=13)

    ax_barrel.set_xlim(-np.pi, np.pi)

    ax_barrel.set_xticks(
        [-np.pi, -np.pi / 2, 0.0, np.pi / 2, np.pi],
        [
            r"$-\pi$",
            r"$-\pi/2$",
            "0",
            r"$\pi/2$",
            r"$\pi$",
        ],
    )

    ax_barrel.axvline(
        0.0,
        linewidth=0.9,
        alpha=0.4,
    )

    ax_barrel.axhline(
        0.0,
        linewidth=0.9,
        alpha=0.4,
    )

    ax_barrel.grid(alpha=0.25)
    ax_barrel.tick_params(axis="both", labelsize=14)

    # ------------------------------------------------------------------
    # Bottom cap
    # ------------------------------------------------------------------

    ax_bottom.scatter(
        all_bottom_x,
        all_bottom_y,
        s=5,
        c="lightgray",
        alpha=0.35,
        linewidths=0,
    )

    if len(hit_bottom_q) > 0:
        sc = ax_bottom.scatter(
            hit_bottom_x,
            hit_bottom_y,
            s=18,
            c=hit_bottom_q,
            cmap="plasma",
            vmin=q_min,
            vmax=q_max,
            linewidths=0,
            alpha=0.95,
        )

    ax_bottom.set_title("Bottom cap", fontsize=14)
    ax_bottom.set_xlabel("x [cm]", fontsize=13)
    ax_bottom.set_ylabel("y [cm]", fontsize=13)

    ax_bottom.set_xlim(-cap_lim, cap_lim)
    ax_bottom.set_ylim(-cap_lim, cap_lim)

    ax_bottom.set_aspect("equal", adjustable="box")
    ax_bottom.set_box_aspect(1)

    ax_bottom.grid(alpha=0.25)
    ax_bottom.tick_params(axis="both", labelsize=14)

    # ------------------------------------------------------------------
    # Shared colorbar
    # ------------------------------------------------------------------

    if sc is not None:
        cbar = fig.colorbar(
            sc,
            cax=cax,
        )

        cbar.set_label(
            "Charge [p.e.]",
            fontsize=13,
        )

        cbar.ax.tick_params(
            labelsize=14,
        )

    else:
        cax.axis("off")

    # ------------------------------------------------------------------
    # Information box
    # ------------------------------------------------------------------

    if "time_span" in row and np.isfinite(row["time_span"]):
        time_span_string = f"{row['time_span']:.1f} ns"

    elif np.isfinite(row["min_time"]) and np.isfinite(row["max_time"]):
        time_span_string = f"{row['max_time'] - row['min_time']:.1f} ns"

    else:
        time_span_string = "nan"

    track_length = row["track_length_cm"]

    if track_length is not None and np.isfinite(track_length):
        length_string = f"{track_length:.2f} cm"
    else:
        length_string = "nan"

    info_text = (
        f"Energy: {energy_display_label(row['energy_MeV'])}\n"
        f"Entry: {row['entry_index']}\n"
        f"Track length: {length_string}\n"
        f"Total charge: {row['tot_charge']:.2f} p.e.\n"
        f"Digitized hits: {row['n_digi_hits']}\n"
        f"Hit PMTs: {row['n_digi_tubes_hit_merged']}\n"
        f"Hit-time span: {time_span_string}\n"
        f"Trigger objects: {row['n_triggers']}"
    )

    fig.text(
        0.02,
        0.985,
        info_text,
        ha="left",
        va="top",
        fontsize=15,
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.88,
            edgecolor="black",
            linewidth=0.9,
        ),
    )

    # ------------------------------------------------------------------
    # Main title
    # ------------------------------------------------------------------

    fig.suptitle(
        (f"2D PMT display - {energy_display_label(row['energy_MeV'])}"),
        fontsize=16,
        y=0.995,
    )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    return True


def print_row_summary(row):
    print()
    print(f"Entry index: {row['entry_index']}")
    print(f"Generated positron energy: {row['energy_MeV']}")
    print(f"Track length: {row['track_length_cm']} cm")
    print(f"Number of WCSim trigger objects: {row['n_triggers']}")
    print(f"Raw hits, trigger-summed: {row['n_raw_hits']}")
    print(f"Digitized hits, trigger-summed: {row['n_digi_hits']}")
    print(f"Raw tubes hit, trigger-summed: {row['n_raw_tubes_hit_sum']}")
    print(f"Digitized tubes hit, trigger-summed: {row['n_digi_tubes_hit_sum']}")
    print(f"Digitized tubes hit, merged: {row['n_digi_tubes_hit_merged']}")
    print(f"Total charge: {row['tot_charge']} p.e.")
    print(f"Minimum hit time: {row['min_time']} ns")
    print(f"Maximum hit time: {row['max_time']} ns")


def run_single_event_mode(rows, hit_tree, pmt_map, entry_index):
    matching = [row for row in rows if row["entry_index"] == entry_index]

    if len(matching) == 0:
        raise RuntimeError(f"Could not find entry_index={entry_index}.")

    if len(matching) > 1:
        raise RuntimeError(f"Found multiple rows with entry_index={entry_index}.")

    row = matching[0]
    print_row_summary(row)

    energy_label = f"{row['energy_MeV']:.3f}_MeV"
    clean_label = sanitize_label(energy_label)
    stem = f"entry_{row['entry_index']}_{clean_label}"

    made_3d = save_3d_display(
        row=row,
        hit_tree=hit_tree,
        pmt_map=pmt_map,
        output_path=OUTPUT_DIR / f"{stem}_3d.html",
    )

    made_2d = save_2d_display(
        row=row,
        hit_tree=hit_tree,
        pmt_map=pmt_map,
        output_path=OUTPUT_DIR / f"{stem}_2d.pdf",
    )

    if made_3d:
        print(f"Saved 3D display: {OUTPUT_DIR / f'{stem}_3d.html'}")
    else:
        print("No valid hit map: 3D display not produced.")

    if made_2d:
        print(f"Saved 2D display: {OUTPUT_DIR / f'{stem}_2d.pdf'}")
    else:
        print("No valid hit map: 2D display not produced.")


def run_full_analysis(rows, hit_tree, pmt_map):

    energies = []
    for row in rows:
        energy = float(row["energy_MeV"])
        if not any(np.isclose(energy, e) for e in energies):
            energies.append(energy)

    for energy in energies:
        energy_label = energy_display_label(energy)
        clean_label = energy_file_label(energy)

        energy_rows = [
            row for row in rows if np.isclose(float(row["energy_MeV"]), energy)
        ]

        energy_dir = OUTPUT_DIR / clean_label
        hist_dir = energy_dir / "histograms"
        display_3d_dir = energy_dir / "display_3d"
        display_2d_dir = energy_dir / "display_2d"

        hist_dir.mkdir(parents=True, exist_ok=True)
        display_3d_dir.mkdir(parents=True, exist_ok=True)
        display_2d_dir.mkdir(parents=True, exist_ok=True)

        print()
        print(f"Energy: {energy_label}")
        print(f"  events: {len(energy_rows)}")

        n_nonzero_raw = sum(row["n_raw_hits"] > 0 for row in energy_rows)
        n_nonzero_digi = sum(row["n_digi_hits"] > 0 for row in energy_rows)
        n_valid_display = sum(has_valid_digihits(row) for row in energy_rows)
        n_multi_trigger = sum(row["n_triggers"] > 1 for row in energy_rows)
        trigger_values, trigger_counts = np.unique(
            np.array([row["n_triggers"] for row in energy_rows], dtype=int),
            return_counts=True,
        )
        trigger_summary = ", ".join(
            f"{value} trigger: {count} event(s)"
            for value, count in zip(trigger_values, trigger_counts)
        )

        print(f"  trigger summary:          {trigger_summary}")
        print(f"  events with raw hits:       {n_nonzero_raw}")
        print(f"  events with digi hits:      {n_nonzero_digi}")
        print(f"  valid display candidates:   {n_valid_display}")
        print(f"  events with >1 trigger:     {n_multi_trigger}")

        save_histograms_for_energy(
            rows=energy_rows,
            energy_label=energy_label,
            output_dir=hist_dir,
        )

        selected = select_representative_events(energy_rows)

        if len(selected) == 0:
            print("  no valid digitized hits: skipping detector displays")
            continue

        if len(selected) < 4:
            print(
                f"  only {len(selected)} valid digitized-hit event(s): "
                "plotting available events only"
            )

        print("  selected events for display:")

        for row in selected:
            length_string = (
                f"{row['track_length_cm']:.2f}"
                if row["track_length_cm"] is not None
                else "None"
            )

            print(
                f"    entry={row['entry_index']} "
                f"L={length_string} cm "
                f"Q={row['tot_charge']:.2f} "
                f"Ndigi={row['n_digi_hits']} "
                f"NPMT={row['n_digi_tubes_hit_merged']} "
                f"Ntrig={row['n_triggers']}"
            )

            stem = (
                f"{clean_label}_entry_{row['entry_index']}"
                f"_Q_{row['tot_charge']:.2f}"
                f"_Ndigi_{row['n_digi_hits']}"
            )

            save_3d_display(
                row=row,
                hit_tree=hit_tree,
                pmt_map=pmt_map,
                output_path=display_3d_dir / f"{stem}.html",
            )

            save_2d_display(
                row=row,
                hit_tree=hit_tree,
                pmt_map=pmt_map,
                output_path=display_2d_dir / f"{stem}.pdf",
            )


def main():
    parser = argparse.ArgumentParser(
        description="Make histograms and detector displays from compact positron ROOT summary."
    )

    parser.add_argument(
        "--summary_root_file",
        type=str,
        help="Compact ROOT summary file containing EventSummary, PmtHitMap, Geometry.",
    )

    parser.add_argument(
        "--entry_index",
        type=int,
        default=None,
        help="If provided, only make 2D/3D displays for this event index.",
    )

    args = parser.parse_args()

    summary_root_file = Path(args.summary_root_file)
    root_file = ROOT.TFile.Open(str(summary_root_file))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open ROOT file: {summary_root_file}")

    event_tree = root_file.Get("EventSummary")
    hit_tree = root_file.Get("PmtHitMap")

    if not event_tree:
        raise RuntimeError("Could not find tree 'EventSummary'.")

    if not hit_tree:
        raise RuntimeError("Could not find tree 'PmtHitMap'.")

    n_event_entries = int(event_tree.GetEntries())
    n_hit_entries = int(hit_tree.GetEntries())

    if n_event_entries != n_hit_entries:
        raise RuntimeError(
            "EventSummary and PmtHitMap have different number of entries: "
            f"{n_event_entries} vs {n_hit_entries}."
        )

    print(f"Input summary ROOT file: {summary_root_file}")
    print(f"EventSummary entries: {n_event_entries}")
    print(f"PmtHitMap entries: {n_hit_entries}")

    pmt_map = load_geometry(root_file)
    print(f"Geometry PMTs: {len(pmt_map)}")

    rows = build_event_rows(
        event_tree=event_tree,
    )

    if args.entry_index is not None:
        run_single_event_mode(
            rows=rows,
            hit_tree=hit_tree,
            pmt_map=pmt_map,
            entry_index=args.entry_index,
        )
    else:
        run_full_analysis(
            rows=rows,
            hit_tree=hit_tree,
            pmt_map=pmt_map,
        )

    root_file.Close()

    print()
    print("Done")


if __name__ == "__main__":
    main()
