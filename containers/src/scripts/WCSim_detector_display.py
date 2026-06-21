#!/usr/bin/env python3

import argparse
import math

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go  # type: ignore
import ROOT  # type: ignore


def load_WCSim_trees(input_file):
    ROOT.gSystem.Load("libWCSimRoot.so")

    root_file = ROOT.TFile.Open(str(input_file))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open ROOT file: {input_file}")

    wcsim_tree = root_file.Get("wcsimT")
    if not wcsim_tree:
        raise RuntimeError("Could not find TTree 'wcsimT'.")

    geo_tree = root_file.Get("wcsimGeoT")
    if not geo_tree:
        raise RuntimeError("Could not find TTree 'wcsimGeoT'.")

    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    geom = ROOT.WCSimRootGeom()
    geo_tree.SetBranchAddress("wcsimrootgeom", ROOT.AddressOf(geom))

    n_entries = int(wcsim_tree.GetEntries())

    return {
        "root_file": root_file,
        "wcsim_tree": wcsim_tree,
        "geo_tree": geo_tree,
        "event": event,
        "geom": geom,
        "n_entries": n_entries,
    }


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

        charge_by_tube[tube_id] = charge
        time_by_tube[tube_id] = time

    return charge_by_tube, time_by_tube


def extract_true_tracks(trigger):
    """
    Extract true WCSim tracks from one trigger.

    Returns a list of dictionaries with particle information.
    """
    tracks = []

    n_tracks = trigger.GetNtrack()
    true_tracks = trigger.GetTracks()

    for i in range(n_tracks):
        trk = true_tracks.At(i)

        ipnu = int(trk.GetIpnu())  # PDG-like code in WCSim
        parent_type = int(trk.GetParenttype())

        start = np.array(
            [
                float(trk.GetStart(0)),
                float(trk.GetStart(1)),
                float(trk.GetStart(2)),
            ]
        )

        stop = np.array(
            [
                float(trk.GetStop(0)),
                float(trk.GetStop(1)),
                float(trk.GetStop(2)),
            ]
        )

        direction = np.array(
            [
                float(trk.GetDir(0)),
                float(trk.GetDir(1)),
                float(trk.GetDir(2)),
            ]
        )

        norm = np.linalg.norm(direction)
        if norm > 0:
            direction = direction / norm

        tracks.append(
            {
                "index": i,
                "ipnu": ipnu,
                "parent_type": parent_type,
                "start": start,
                "stop": stop,
                "direction": direction,
                "p": float(trk.GetP()),
                "E": float(trk.GetE()),
                "time": float(trk.GetTime()),
            }
        )

    return tracks


def filter_tracks(tracks):
    """
    Filter tracks based on criteria, e.g. parent_type == 0 (primary particles).
    """
    primary_tracks = []
    secondary_tracks = []
    for track in tracks:
        if (
            track["parent_type"] == 0
            and track["ipnu"] == -13
            and (track["E"] > track["p"])
        ):
            primary_tracks.append(track)
            if len(primary_tracks) > 1:
                print(
                    f"Warning: multiple primary tracks found. "
                    f"Track {track['index']} also matches criteria."
                )
        if (
            track["parent_type"] == -13
            and track["ipnu"] == -11
            and track["E"] >= track["p"]
            and (track["start"] == primary_tracks[0]["stop"]).all()
        ):
            secondary_tracks.append(track)
            if len(secondary_tracks) > 1:
                print(
                    f"Warning: multiple secondary tracks found. "
                    f"Track {track['index']} also matches criteria."
                )
    return primary_tracks, secondary_tracks


def make_2D_event_display(
    input_file,
    output_file,
    event_index=0,
    trigger_index=0,
):
    data = load_WCSim_trees(input_file)

    wcsim_tree = data["wcsim_tree"]
    geo_tree = data["geo_tree"]
    event = data["event"]
    geom = data["geom"]
    n_entries = data["n_entries"]

    if event_index < 0 or event_index >= n_entries:
        raise IndexError(
            f"event_index={event_index} outside valid range [0, {n_entries - 1}]"
        )

    wcsim_tree.GetEntry(event_index)
    geo_tree.GetEntry(0)

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
    fig.savefig(str(output_file) + ".pdf", dpi=1200)
    plt.close(fig)

    print(f"Saved: {output_file}.pdf")
    print(f"Number of hit PMTs: {len(hit_q)}")
    if len(hit_q) > 0:
        print(f"Total charge: {hit_q.sum():.2f} p.e.")
        print(f"Max PMT charge: {hit_q.max():.2f} p.e.")


def get_track_points(track):
    """Return start, stop, direction and real track length in cm."""
    start = np.asarray(track["start"], dtype=float)
    stop = np.asarray(track["stop"], dtype=float)

    vector = stop - start
    length = float(np.linalg.norm(vector))
    direction = vector / length

    return start, stop, direction, length


def print_track_summary(label, track, length_cm):
    """Print compact true-track information useful for debugging displays."""
    print(
        f"{label} true track summary:\n"
        f"  PDG ipnu              = {track['ipnu']}\n"
        f"  parent_type           = {track['parent_type']}\n"
        f"  momentum |p|          = {track['p']:.3f} MeV/c\n"
        f"  energy E              = {track['E']:.3f} MeV\n"
        f"  real track length     = {length_cm:.3f} cm\n"
        f"  start                 = {track['start']} cm\n"
        f"  stop                  = {track['stop']} cm\n"
    )


def add_scaled_track_arrow(
    fig,
    start,
    direction,
    display_length_cm,
    name,
    color,
    line_width=7,
):
    """Draw an artificially-scaled 3D arrow from start along direction.

    The line length is display_length_cm. The cone is only the arrow head.
    """
    display_stop = start + display_length_cm * direction

    fig.add_trace(
        go.Scatter3d(
            x=[start[0], display_stop[0]],
            y=[start[1], display_stop[1]],
            z=[start[2], display_stop[2]],
            mode="lines",
            line=dict(width=line_width, color=color),
            name=name,
        )
    )

    # Size the cone with the displayed track, but avoid it becoming invisible.
    cone_size = max(150.0, 0.10 * display_length_cm)

    fig.add_trace(
        go.Cone(
            x=[display_stop[0]],
            y=[display_stop[1]],
            z=[display_stop[2]],
            u=[direction[0]],
            v=[direction[1]],
            w=[direction[2]],
            sizemode="absolute",
            sizeref=cone_size,
            anchor="tip",
            name=f"{name} arrow head",
            showscale=False,
        )
    )


def make_3D_event_display(
    input_file,
    output_file,
    event_index=0,
    trigger_index=0,
):
    """
    Make an interactive 3D WCSim event display.

    PMTs are drawn at their real WCSim positions.
    Hit PMTs are colored by digitized charge.
    """
    data = load_WCSim_trees(input_file)

    wcsim_tree = data["wcsim_tree"]
    geo_tree = data["geo_tree"]
    event = data["event"]
    geom = data["geom"]
    n_entries = data["n_entries"]

    if event_index < 0 or event_index >= n_entries:
        raise IndexError(
            f"event_index={event_index} outside valid range [0, {n_entries - 1}]"
        )

    wcsim_tree.GetEntry(event_index)
    geo_tree.GetEntry(0)

    pmt_map = build_pmt_map(geom)
    charge_by_tube, _ = collect_digitized_hits(
        event,
        trigger_index=trigger_index,
    )

    all_x, all_y, all_z = [], [], []
    hit_x, hit_y, hit_z, hit_q = [], [], [], []

    for tube_id, pmt in pmt_map.items():
        x = pmt["x"]
        y = pmt["y"]
        z = pmt["z"]

        all_x.append(x)
        all_y.append(y)
        all_z.append(z)

        if tube_id in charge_by_tube:
            hit_x.append(x)
            hit_y.append(y)
            hit_z.append(z)
            hit_q.append(charge_by_tube[tube_id])

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

    # Draw particle direction arrow.
    trigger = event.GetTrigger(trigger_index)
    tracks = extract_true_tracks(trigger)
    muon_track, electron_track = filter_tracks(tracks)

    muon_start, _, muon_dir, muon_length = get_track_points(muon_track[0])
    electron_start, _, electron_dir, electron_length = get_track_points(
        electron_track[0]
    )

    print_track_summary("Muon", muon_track[0], muon_length)
    print_track_summary("Electron", electron_track[0], electron_length)

    # Artificial display scaling. The longest real track is drawn with this
    # length; the other one is scaled by the same factor.
    max_display_track_length_cm = 2500.0
    max_real_track_length_cm = max(muon_length, electron_length)

    display_scale = max_display_track_length_cm / max_real_track_length_cm

    muon_display_length = muon_length * display_scale
    electron_display_length = electron_length * display_scale

    print(
        "Artificial display scale:\n"
        f"  scale factor           = {display_scale:.3f}\n"
        f"  muon display length   = {muon_display_length:.3f} cm\n"
        f"  electron display length = {electron_display_length:.3f} cm\n"
    )

    add_scaled_track_arrow(
        fig=fig,
        start=muon_start,
        direction=muon_dir,
        display_length_cm=muon_display_length,
        name="muon true direction",
        color="green",
    )

    add_scaled_track_arrow(
        fig=fig,
        start=electron_start,
        direction=electron_dir,
        display_length_cm=electron_display_length,
        name="electron true direction",
        color="red",
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

    fig.write_html(str(output_file) + ".html")


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "input_file",
        type=str,
        help="Input WCSim ROOT file.",
    )
    argument_parser.add_argument(
        "output_file",
        type=str,
        help="Output PDF or HTML file for the event display.",
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
    argument_parser.add_argument(
        "--display_3D",
        action="store_true",
        help="If set, create an interactive 3D event display instead of 2D.",
    )
    args = argument_parser.parse_args()
    if args.display_3D:
        make_3D_event_display(
            input_file=args.input_file,
            output_file=args.output_file,
            event_index=args.event_index,
            trigger_index=args.trigger_index,
        )
    else:
        make_2D_event_display(
            input_file=args.input_file,
            output_file=args.output_file,
            event_index=args.event_index,
            trigger_index=args.trigger_index,
        )


if __name__ == "__main__":
    main()
