#!/usr/bin/env python3

import argparse
import math

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import ROOT  # type: ignore


def load_wcsim_library():
    """
    Load WCSim ROOT dictionary.

    This requires that the WCSim environment has already been sourced,
    e.g. this_wcsim.sh or your container setup script.
    """
    status = ROOT.gSystem.Load("libWCSimRoot.so")
    if status < 0:
        raise RuntimeError(
            "Could not load libWCSimRoot.so. "
            "Make sure you sourced the WCSim environment inside the container."
        )


def get_geometry(root_file):
    """
    Read WCSim geometry from wcsimGeoT.
    """
    geo_tree = root_file.Get("wcsimGeoT")
    if not geo_tree:
        raise RuntimeError("Could not find tree wcsimGeoT in file.")

    # The geometry is assumed to be the same for all entries
    geo_tree.GetEntry(0)
    # Return the geometry object linked to the branch "wcsimrootgeom".
    # The geometry data is stored in the branch, setting the address of
    # the geom object to the branch allows to read the geometry data
    # into the geom object.
    return geo_tree.wcsimrootgeom


def get_event(root_file, event_index):
    """
    Read one WCSim event from wcsimT.
    """
    event_tree = root_file.Get("wcsimT")
    event_tree.GetEntry(event_index)
    return event_tree.wcsimrootevent


def build_pmt_map(geom):
    """
    Build dictionary:

        tube_id -> PMT geometry information

    WCSim tube IDs are usually 1-based, while GetPMT(i) uses a 0-based index.
    """
    n_pmts = int(geom.GetWCNumPMT())

    pmt_map = {}

    for i in range(n_pmts):
        pmt = geom.GetPMT(i)

        tube_id = int(pmt.GetTubeNo())
        cyl_loc = int(pmt.GetCylLoc())

        x = float(pmt.GetPosition(0))
        y = float(pmt.GetPosition(1))
        z = float(pmt.GetPosition(2))

        pmt_map[tube_id] = {
            "x": x,
            "y": y,
            "z": z,
            "cyl_loc": cyl_loc,
        }

    return pmt_map


def project_pmt_to_2d(pmt, radius):
    """
    Project one PMT position to a 2D detector-display coordinate.

    WCSim convention from the documentation:
      cyl_loc = 0: top cap
      cyl_loc = 1: barrel wall
      cyl_loc = 2: bottom cap

    Simple layout:

        top cap disk      barrel rectangle      bottom cap disk
    """
    x = pmt["x"]
    y = pmt["y"]
    z = pmt["z"]
    cyl_loc = pmt["cyl_loc"]

    # Barrel rectangle dimensions.
    barrel_width = 2.0 * math.pi * radius

    # Gaps between detector parts.
    gap = 0.25 * radius

    if cyl_loc == 1:
        # Barrel: unwrap cylinder.
        phi = math.atan2(y, x)

        u = radius * phi
        v = z

        region = "barrel"

    elif cyl_loc == 0:
        # Top cap: put disk to the left of the barrel.
        u = -0.5 * barrel_width - gap - radius + x
        v = y

        region = "top"

    elif cyl_loc == 2:
        # Bottom cap: put disk to the right of the barrel.
        u = 0.5 * barrel_width + gap + radius + x
        v = y

        region = "bottom"

    else:
        # Unknown region; fall back to x-y.
        u = x
        v = y
        region = "unknown"

    return u, v, region


def collect_digitized_hits(event, trigger_index=0):
    """
    Return dictionary:

        tube_id -> total digitized charge

    If time_min/time_max are provided, only hits in that time window are used.
    """
    trigger = event.GetTrigger(trigger_index)

    n_hits = int(trigger.GetNcherenkovdigihits())
    digi_hits = trigger.GetCherenkovDigiHits()

    charge_by_tube = {}
    time_by_tube = {}

    for i in range(n_hits):
        hit = digi_hits.At(i)

        tube_id = int(hit.GetTubeId())
        charge = float(hit.GetQ())
        time = float(hit.GetT())

        charge_by_tube[tube_id] = charge_by_tube.get(tube_id, 0.0) + charge

        # For display/debugging: keep earliest digitized time per tube.
        if tube_id not in time_by_tube:
            time_by_tube[tube_id] = time
        else:
            time_by_tube[tube_id] = min(time_by_tube[tube_id], time)

    return charge_by_tube, time_by_tube


def make_event_display(
    input_file,
    output_pdf,
    event_index=0,
    trigger_index=0,
):
    load_wcsim_library()

    root_file = ROOT.TFile.Open(input_file)
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open ROOT file: {input_file}")

    geom = get_geometry(root_file)
    event = get_event(root_file, event_index)

    radius = float(geom.GetWCCylRadius())

    pmt_map = build_pmt_map(geom)
    charge_by_tube, _ = collect_digitized_hits(
        event,
        trigger_index=trigger_index,
    )

    all_u = []
    all_v = []

    hit_u = []
    hit_v = []
    hit_q = []

    for tube_id, pmt in pmt_map.items():
        u, v, _ = project_pmt_to_2d(pmt, radius)

        all_u.append(u)
        all_v.append(v)

        if tube_id in charge_by_tube:
            hit_u.append(u)
            hit_v.append(v)
            hit_q.append(charge_by_tube[tube_id])

    all_u = np.asarray(all_u)
    all_v = np.asarray(all_v)

    hit_u = np.asarray(hit_u)
    hit_v = np.asarray(hit_v)
    hit_q = np.asarray(hit_q)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(
        all_u,
        all_v,
        s=4,
        c="lightgray",
        alpha=0.35,
        linewidths=0,
        label="all PMTs",
    )

    if len(hit_q) > 0:
        sc = ax.scatter(
            hit_u,
            hit_v,
            s=10,
            c=hit_q,
            cmap="plasma",
            linewidths=0,
            label="hit PMTs",
        )

        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label("Charge [p.e.]")
    else:
        print("Warning: no digitized hits found for this event/time window.")

    title = f"WCSim event display: event {event_index}, trigger {trigger_index}"

    ax.set_title(title)
    ax.set_xlabel("2D unwrapped detector coordinate")
    ax.set_ylabel("2D detector coordinate")

    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(output_pdf, dpi=1200)
    plt.close(fig)

    print(f"Saved: {output_pdf}")
    print(f"Number of hit PMTs: {len(hit_q)}")
    if len(hit_q) > 0:
        print(f"Total charge: {hit_q.sum():.2f} p.e.")
        print(f"Max PMT charge: {hit_q.max():.2f} p.e.")


def make_3d_event_display(
    pmt_map,
    hit_charge,
    output_html,
    event_index=0,
    trigger_index=0,
    vertex=(0.0, 0.0, 0.0),
    direction=(1.0, 0.0, 0.0),
):
    """
    Make an interactive 3D WCSim event display.

    PMTs are drawn at their real WCSim positions.
    Hit PMTs are colored by digitized charge.
    """

    all_x, all_y, all_z = [], [], []
    hit_x, hit_y, hit_z, hit_q = [], [], [], []

    for tube_id, pmt in pmt_map.items():
        x = pmt["x"]
        y = pmt["y"]
        z = pmt["z"]

        all_x.append(x)
        all_y.append(y)
        all_z.append(z)

        if tube_id in hit_charge:
            hit_x.append(x)
            hit_y.append(y)
            hit_z.append(z)
            hit_q.append(hit_charge[tube_id])

    fig = go.Figure()

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
        )
    )

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
            text=[f"charge = {q:.2f} p.e." for q in hit_q],
        )
    )

    # Draw particle direction arrow approximately.
    vx, vy, vz = vertex
    dx, dy, dz = direction
    norm = np.sqrt(dx * dx + dy * dy + dz * dz)

    if norm > 0:
        dx /= norm
        dy /= norm
        dz /= norm

        arrow_length = 3000.0  # cm, adjust depending on detector size

        fig.add_trace(
            go.Cone(
                x=[vx + arrow_length * dx],
                y=[vy + arrow_length * dy],
                z=[vz + arrow_length * dz],
                u=[dx],
                v=[dy],
                w=[dz],
                sizemode="absolute",
                sizeref=400,
                name="gun direction",
                showscale=False,
            )
        )

        fig.add_trace(
            go.Scatter3d(
                x=[vx, vx + arrow_length * dx],
                y=[vy, vy + arrow_length * dy],
                z=[vz, vz + arrow_length * dz],
                mode="lines",
                name="particle direction",
                line=dict(width=6),
            )
        )

    fig.update_layout(
        title=f"WCSim 3D event display: event {event_index}, trigger {trigger_index}",
        scene=dict(
            xaxis_title="x [cm]",
            yaxis_title="y [cm]",
            zaxis_title="z [cm]",
            aspectmode="data",
        ),
        legend=dict(x=0.02, y=0.98),
    )

    fig.write_html(output_html)


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "input_file",
        type=str,
        help="Input WCSim ROOT file.",
    )
    argument_parser.add_argument(
        "output_pdf",
        type=str,
        help="Output PDF file for the event display.",
    )
    argument_parser.add_argument(
        "--event_index",
        type=int,
        default=0,
        help="Index of the event to display (default: 0).",
    )
    argument_parser.add_argument(
        "--trigger_index",
        type=int,
        default=0,
        help="Index of the trigger to display (default: 0).",
    )
    args = argument_parser.parse_args()
    make_event_display(
        input_file=args.input_file,
        output_pdf=args.output_pdf,
        event_index=args.event_index,
        trigger_index=args.trigger_index,
    )


if __name__ == "__main__":
    main()
