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


def load_geometry(root_file):
    """
    Read compact Geometry tree.

    Returns
    -------
    pmt_pos_by_tube : dict
        tube_id -> np.array([x, y, z])
    """

    geo_tree = root_file.Get("Geometry")
    if not geo_tree:
        raise RuntimeError("Could not find tree 'Geometry' in input file.")

    if int(geo_tree.GetEntries()) < 1:
        raise RuntimeError("Geometry tree exists but has no entries.")

    geo_tree.GetEntry(0)

    pmt_pos_by_tube = {}

    tube_ids = list(geo_tree.tube_id)
    xs = list(geo_tree.x)
    ys = list(geo_tree.y)
    zs = list(geo_tree.z)

    for tube_id, x, y, z in zip(tube_ids, xs, ys, zs):
        pmt_pos_by_tube[int(tube_id)] = np.array(
            [float(x), float(y), float(z)],
            dtype=float,
        )

    return pmt_pos_by_tube


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

        row = {
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
            "min_time": float(event_tree.min_time),
            "max_time": float(event_tree.max_time),
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


def choose_bins(values, key):
    """
    Choose reasonable histogram bins.

    Integer count variables get integer-centered bins.
    Continuous variables use Freedman-Diaconis when possible.
    """

    if len(values) == 0:
        return 40

    integer_keys = {
        "n_triggers",
        "n_raw_hits",
        "n_digi_hits",
        "n_raw_tubes_hit_sum",
        "n_digi_tubes_hit_sum",
        "n_digi_tubes_hit_merged",
    }

    if key in integer_keys:
        vmin = int(np.min(values))
        vmax = int(np.max(values))

        return np.arange(vmin - 0.5, vmax + 1.5, 1.0).tolist()

    if len(values) < 2:
        return 10

    return "fd"


def save_histogram(rows, key, xlabel, title, output_path):
    values = [row[key] for row in rows if np.isfinite(row[key])]

    if len(values) == 0:
        return False

    bins = choose_bins(values, key)

    plt.figure(figsize=(8, 6))
    plt.hist(values, bins=bins, histtype="step", linewidth=1.8)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel("Events", fontsize=14)
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
        ("min_time", "minimum digitized hit time [ns]"),
        ("max_time", "maximum digitized hit time [ns]"),
        ("n_raw_tubes_hit_sum", "number of raw tubes hit, trigger-summed"),
        ("n_digi_tubes_hit_sum", "number of digitized tubes hit, trigger-summed"),
        ("n_digi_tubes_hit_merged", "number of digitized tubes hit, merged"),
        ("tot_charge", "total collected charge [p.e.]"),
        ("n_triggers", "number of WCSim trigger objects"),
    ]

    for key, xlabel in variables:
        output_path = output_dir / f"{key}.pdf"
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


def save_3d_display(row, hit_tree, pmt_pos_by_tube, output_path):
    tube_ids, charges, times = read_hit_map_for_row(hit_tree, row)

    if len(tube_ids) == 0:
        return False

    xs = []
    ys = []
    zs = []
    qs = []
    texts = []

    for tube_id, charge, time in zip(tube_ids, charges, times):
        tube_id = int(tube_id)

        if tube_id not in pmt_pos_by_tube:
            continue

        pos = pmt_pos_by_tube[tube_id]

        xs.append(pos[0])
        ys.append(pos[1])
        zs.append(pos[2])
        qs.append(float(charge))
        texts.append(
            f"tube={tube_id}<br>q={float(charge):.3f} p.e.<br>t={float(time):.3f} ns"
        )

    if len(xs) == 0:
        return False

    fig = go.Figure()

    fig.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="markers",
            marker=dict(
                size=4,
                color=qs,
                colorscale="Viridis",
                colorbar=dict(title="charge [p.e.]"),
                opacity=0.9,
            ),
            text=texts,
            name="hit PMTs",
        )
    )

    start = row["true_start"]
    stop = row["true_stop"]

    if np.all(np.isfinite(start)) and np.all(np.isfinite(stop)):
        fig.add_trace(
            go.Scatter3d(
                x=[start[0], stop[0]],
                y=[start[1], stop[1]],
                z=[start[2], stop[2]],
                mode="lines+markers",
                line=dict(width=8),
                marker=dict(size=5),
                name="true positron track",
            )
        )

    length_string = (
        f"{row['track_length_cm']:.2f} cm"
        if row["track_length_cm"] is not None
        else "None"
    )

    title = (
        f"{row['energy_label']} | entry {row['entry_index']} | "
        f"L={length_string} | "
        f"Q={row['tot_charge']:.2f} p.e. | "
        f"Ndigi={row['n_digi_hits']} | "
        f"NPMT={row['n_digi_tubes_hit_merged']} | "
        f"Ntrig={row['n_triggers']}"
    )

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="x [cm]",
            yaxis_title="y [cm]",
            zaxis_title="z [cm]",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, b=0, t=50),
    )

    fig.write_html(str(output_path))

    return True


def save_2d_display(row, hit_tree, pmt_pos_by_tube, output_path):
    """
    Simple 2D unwrapped PMT display.

    x-axis: PMT azimuth phi
    y-axis: PMT z position
    color: merged charge
    """

    tube_ids, charges, times = read_hit_map_for_row(hit_tree, row)

    if len(tube_ids) == 0:
        return False

    phis = []
    zs = []
    qs = []

    for tube_id, charge in zip(tube_ids, charges):
        tube_id = int(tube_id)

        if tube_id not in pmt_pos_by_tube:
            continue

        x, y, z = pmt_pos_by_tube[tube_id]
        phi = np.arctan2(y, x)

        phis.append(phi)
        zs.append(z)
        qs.append(float(charge))

    if len(phis) == 0:
        return False

    plt.figure(figsize=(9, 6))
    sc = plt.scatter(
        phis,
        zs,
        c=qs,
        s=12,
        alpha=0.9,
    )
    plt.colorbar(sc, label="charge [p.e.]")
    plt.xlabel(r"$\phi$ [rad]", fontsize=14)
    plt.ylabel("z [cm]", fontsize=14)

    length_string = (
        f"{row['track_length_cm']:.2f} cm"
        if row["track_length_cm"] is not None
        else "None"
    )

    title = (
        f"{row['energy_label']} | entry {row['entry_index']} | "
        f"L={length_string} | "
        f"Q={row['tot_charge']:.2f} p.e."
    )

    plt.title(title, fontsize=13)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return True


def print_row_summary(row):
    print()
    print(f"Entry index: {row['entry_index']}")
    print(f"Generated positron energy: {row['energy_label']}")
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


def run_single_event_mode(rows, hit_tree, pmt_pos_by_tube, entry_index):
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
        pmt_pos_by_tube=pmt_pos_by_tube,
        output_path=OUTPUT_DIR / f"{stem}_3d.html",
    )

    made_2d = save_2d_display(
        row=row,
        hit_tree=hit_tree,
        pmt_pos_by_tube=pmt_pos_by_tube,
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


def run_full_analysis(rows, hit_tree, pmt_pos_by_tube):

    energy_labels = []
    for row in rows:
        energy_label = f"{row['energy_MeV']:.3f}_MeV"
        if energy_label not in energy_labels:
            energy_labels.append(energy_label)

    for energy_label_i in energy_labels:
        energy_label = f"{energy_label_i}"
        energy_rows = [
            row for row in rows if f"{row['energy_MeV']:.3f}_MeV" == energy_label_i
        ]

        clean_label = sanitize_label(energy_label_i)

        energy_dir = OUTPUT_DIR / clean_label
        hist_dir = energy_dir / "histograms"
        display_3d_dir = energy_dir / "display_3d"
        display_2d_dir = energy_dir / "display_2d"

        hist_dir.mkdir(parents=True, exist_ok=True)
        display_3d_dir.mkdir(parents=True, exist_ok=True)
        display_2d_dir.mkdir(parents=True, exist_ok=True)

        print()
        print(f"Energy: {energy_label_i}")
        print(f"  events: {len(energy_rows)}")

        n_nonzero_raw = sum(row["n_raw_hits"] > 0 for row in energy_rows)
        n_nonzero_digi = sum(row["n_digi_hits"] > 0 for row in energy_rows)
        n_valid_display = sum(has_valid_digihits(row) for row in energy_rows)
        n_multi_trigger = sum(row["n_triggers"] > 1 for row in energy_rows)

        print(f"  events with raw hits:       {n_nonzero_raw}")
        print(f"  events with digi hits:      {n_nonzero_digi}")
        print(f"  valid display candidates:   {n_valid_display}")
        print(f"  events with >1 trigger:     {n_multi_trigger}")

        save_histograms_for_energy(
            rows=energy_rows,
            energy_label=energy_label_i,
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
                pmt_pos_by_tube=pmt_pos_by_tube,
                output_path=display_3d_dir / f"{stem}.html",
            )

            save_2d_display(
                row=row,
                hit_tree=hit_tree,
                pmt_pos_by_tube=pmt_pos_by_tube,
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

    pmt_pos_by_tube = load_geometry(root_file)
    print(f"Geometry PMTs: {len(pmt_pos_by_tube)}")

    rows = build_event_rows(
        event_tree=event_tree,
    )

    if args.entry_index is not None:
        run_single_event_mode(
            rows=rows,
            hit_tree=hit_tree,
            pmt_pos_by_tube=pmt_pos_by_tube,
            entry_index=args.entry_index,
        )
    else:
        run_full_analysis(
            rows=rows,
            hit_tree=hit_tree,
            pmt_pos_by_tube=pmt_pos_by_tube,
        )

    root_file.Close()

    print()
    print("Done")


if __name__ == "__main__":
    main()
