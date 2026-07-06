#!/usr/bin/env python3
"""
Create a compact ROOT summary for fixed-energy positron WCSim samples.

The output ROOT file contains:

    1. EventSummary
        One flat entry per WCSim event.

    2. PmtHitMap
        One entry per WCSim event, with variable-length vectors containing
        the merged digitized PMT hit map.

    3. Geometry
        One entry containing the PMT geometry vectors.

For events with more than one WCSim trigger object:
    - scalar hit counters are summed over triggers;
    - PMT charges are summed if the same tube appears in more than one trigger;
    - PMT time is the earliest digitized time among triggers.
"""

import argparse
from array import array
from pathlib import Path

import numpy as np
import ROOT  # type: ignore


def load_wcsim_library():
    ROOT.gSystem.Load("libWCSimRoot.so")


def get_tracks(trigger):
    """Return a list of dictionaries with true particle information."""

    tracks = []

    n_tracks = int(trigger.GetNtrack())
    true_tracks = trigger.GetTracks()

    for i in range(n_tracks):
        trk = true_tracks.At(i)

        start = np.array(
            [
                float(trk.GetStart(0)),
                float(trk.GetStart(1)),
                float(trk.GetStart(2)),
            ],
            dtype=float,
        )

        stop = np.array(
            [
                float(trk.GetStop(0)),
                float(trk.GetStop(1)),
                float(trk.GetStop(2)),
            ],
            dtype=float,
        )

        direction = np.array(
            [
                float(trk.GetDir(0)),
                float(trk.GetDir(1)),
                float(trk.GetDir(2)),
            ],
            dtype=float,
        )

        norm = np.linalg.norm(direction)
        if norm > 0:
            direction = direction / norm

        mass = float(trk.GetM())
        energy = float(trk.GetE())

        tracks.append(
            {
                "index": int(i),
                "ipnu": int(trk.GetIpnu()),
                "parent_type": int(trk.GetParenttype()),
                "creator": str(trk.GetCreatorProcessName()),
                "start": start,
                "stop": stop,
                "direction": direction,
                "M": mass,
                "p": float(trk.GetP()),
                "E": energy,
                "K": energy - mass,
                "time": float(trk.GetTime()),
            }
        )

    return tracks


def find_primary_positron_track(tracks, entry_index):
    """
    Find the generated primary positron/electron track.
    """

    candidates = []

    for trk in tracks:
        if (
            abs(int(trk["ipnu"])) == 11
            and int(trk["parent_type"]) == 0
            and float(trk["M"]) > 0
            and str(trk["creator"]) == "initial"
        ):
            candidates.append(trk)

    if len(candidates) != 1:
        print(
            f"WARNING: entry {entry_index}: found {len(candidates)} "
            "primary positron/electron candidates, expected 1."
        )
        return None

    return candidates[0]


def merge_trigger_hits_from_event(event):
    """
    Merge digitized hit information from all WCSim trigger objects.

    Returns
    -------
    merged : dict
        Event-level counters and merged PMT hit maps.
    """

    n_triggers = int(event.GetNumberOfEvents())

    charge_by_tube = {}
    time_by_tube = {}

    n_raw_hits_sum = 0
    n_digi_hits_sum = 0
    n_raw_tubes_hit_sum = 0
    n_digi_tubes_hit_sum = 0

    first_trigger_tracks = None

    for trigger_index in range(n_triggers):
        trigger = event.GetTrigger(trigger_index)

        if trigger_index == 0:
            first_trigger_tracks = get_tracks(trigger)

        n_raw_hits_sum += int(trigger.GetNcherenkovhits())
        n_digi_hits_sum += int(trigger.GetNcherenkovdigihits())
        n_raw_tubes_hit_sum += int(trigger.GetNumTubesHit())
        n_digi_tubes_hit_sum += int(trigger.GetNumDigiTubesHit())

        digi_hits = trigger.GetCherenkovDigiHits()
        n_digi_hits = int(trigger.GetNcherenkovdigihits())

        for i in range(n_digi_hits):
            hit = digi_hits.At(i)

            tube_id = int(hit.GetTubeId())
            charge = float(hit.GetQ())
            time = float(hit.GetT())

            charge_by_tube[tube_id] = charge_by_tube.get(tube_id, 0.0) + charge

            if tube_id not in time_by_tube:
                time_by_tube[tube_id] = time
            else:
                time_by_tube[tube_id] = min(time_by_tube[tube_id], time)

    times = list(time_by_tube.values())

    merged = {
        "n_triggers": n_triggers,
        "n_raw_hits": n_raw_hits_sum,
        "n_digi_hits": n_digi_hits_sum,
        "n_raw_tubes_hit_sum": n_raw_tubes_hit_sum,
        "n_digi_tubes_hit_sum": n_digi_tubes_hit_sum,
        "n_digi_tubes_hit_merged": len(charge_by_tube),
        "tot_charge": float(sum(charge_by_tube.values())),
        "min_time": float(min(times)) if times else np.nan,
        "max_time": float(max(times)) if times else np.nan,
        "charge_by_tube": charge_by_tube,
        "time_by_tube": time_by_tube,
        "first_trigger_tracks": first_trigger_tracks,
    }

    return merged


def fill_geometry_tree(input_root_file, output_root_file):
    """
    Copy PMT geometry into a compact Geometry tree.

    One entry, with vectors:
        tube_id, x, y, z, cyl_loc

    WCSim convention:
        cyl_loc = 0: top cap
        cyl_loc = 1: barrel wall
        cyl_loc = 2: bottom cap
    """

    geo_tree_in = input_root_file.Get("wcsimGeoT")
    if not geo_tree_in:
        raise RuntimeError("Could not find tree 'wcsimGeoT' in input file.")

    geom = ROOT.WCSimRootGeom()
    geo_tree_in.SetBranchAddress("wcsimrootgeom", ROOT.AddressOf(geom))
    geo_tree_in.GetEntry(0)

    output_root_file.cd()

    geo_tree = ROOT.TTree("Geometry", "Compact PMT geometry")

    tube_id_vec = ROOT.std.vector("int")()
    cyl_loc_vec = ROOT.std.vector("int")()
    x_vec = ROOT.std.vector("float")()
    y_vec = ROOT.std.vector("float")()
    z_vec = ROOT.std.vector("float")()

    geo_tree.Branch("tube_id", tube_id_vec)
    geo_tree.Branch("cyl_loc", cyl_loc_vec)
    geo_tree.Branch("x", x_vec)
    geo_tree.Branch("y", y_vec)
    geo_tree.Branch("z", z_vec)

    n_pmts = int(geom.GetWCNumPMT())

    for i in range(n_pmts):
        pmt = geom.GetPMT(i)

        tube_id_vec.push_back(int(pmt.GetTubeNo()))
        cyl_loc_vec.push_back(int(pmt.GetCylLoc()))
        x_vec.push_back(float(pmt.GetPosition(0)))
        y_vec.push_back(float(pmt.GetPosition(1)))
        z_vec.push_back(float(pmt.GetPosition(2)))

    geo_tree.Fill()
    geo_tree.Write()

    print(f"Saved Geometry tree with {n_pmts} PMTs")


def create_output_trees(output_root_file):
    """
    Create EventSummary and PmtHitMap trees with their branches.
    """

    output_root_file.cd()

    event_tree = ROOT.TTree("EventSummary", "Flat per-event positron summary")
    hit_tree = ROOT.TTree("PmtHitMap", "Merged per-event PMT hit map")

    # Scalars for EventSummary
    event_branch = {
        "entry_index": array("i", [0]),
        "energy_MeV": array("f", [np.nan]),
        "track_length_cm": array("f", [np.nan]),
        "n_triggers": array("i", [0]),
        "n_raw_hits": array("i", [0]),
        "n_digi_hits": array("i", [0]),
        "n_raw_tubes_hit_sum": array("i", [0]),
        "n_digi_tubes_hit_sum": array("i", [0]),
        "n_digi_tubes_hit_merged": array("i", [0]),
        "tot_charge": array("f", [np.nan]),
        "min_time": array("f", [np.nan]),
        "max_time": array("f", [np.nan]),
        "true_p": array("f", [np.nan]),
        "true_E": array("f", [np.nan]),
        "true_K": array("f", [np.nan]),
        "true_M": array("f", [np.nan]),
        "true_time": array("f", [np.nan]),
        "true_ipnu": array("i", [0]),
        "true_parent_type": array("i", [0]),
        "true_start": array("f", [np.nan, np.nan, np.nan]),
        "true_stop": array("f", [np.nan, np.nan, np.nan]),
        "true_dir": array("f", [np.nan, np.nan, np.nan]),
    }

    event_tree.Branch("entry_index", event_branch["entry_index"], "entry_index/I")
    event_tree.Branch("energy_MeV", event_branch["energy_MeV"], "energy_MeV/F")
    event_tree.Branch(
        "track_length_cm",
        event_branch["track_length_cm"],
        "track_length_cm/F",
    )
    event_tree.Branch("n_triggers", event_branch["n_triggers"], "n_triggers/I")
    event_tree.Branch("n_raw_hits", event_branch["n_raw_hits"], "n_raw_hits/I")
    event_tree.Branch("n_digi_hits", event_branch["n_digi_hits"], "n_digi_hits/I")
    event_tree.Branch(
        "n_raw_tubes_hit_sum",
        event_branch["n_raw_tubes_hit_sum"],
        "n_raw_tubes_hit_sum/I",
    )
    event_tree.Branch(
        "n_digi_tubes_hit_sum",
        event_branch["n_digi_tubes_hit_sum"],
        "n_digi_tubes_hit_sum/I",
    )
    event_tree.Branch(
        "n_digi_tubes_hit_merged",
        event_branch["n_digi_tubes_hit_merged"],
        "n_digi_tubes_hit_merged/I",
    )
    event_tree.Branch("tot_charge", event_branch["tot_charge"], "tot_charge/F")
    event_tree.Branch("min_time", event_branch["min_time"], "min_time/F")
    event_tree.Branch("max_time", event_branch["max_time"], "max_time/F")

    event_tree.Branch("true_start", event_branch["true_start"], "true_start[3]/F")
    event_tree.Branch("true_stop", event_branch["true_stop"], "true_stop[3]/F")
    event_tree.Branch("true_dir", event_branch["true_dir"], "true_dir[3]/F")
    event_tree.Branch("true_p", event_branch["true_p"], "true_p/F")
    event_tree.Branch("true_E", event_branch["true_E"], "true_E/F")
    event_tree.Branch("true_K", event_branch["true_K"], "true_K/F")
    event_tree.Branch("true_M", event_branch["true_M"], "true_M/F")
    event_tree.Branch("true_time", event_branch["true_time"], "true_time/F")
    event_tree.Branch("true_ipnu", event_branch["true_ipnu"], "true_ipnu/I")
    event_tree.Branch(
        "true_parent_type",
        event_branch["true_parent_type"],
        "true_parent_type/I",
    )

    # Scalars and vectors for PmtHitMap
    hit_branch = {
        "entry_index": array("i", [0]),
        "tube_id": ROOT.std.vector("int")(),
        "charge": ROOT.std.vector("float")(),
        "time": ROOT.std.vector("float")(),
    }

    hit_tree.Branch("entry_index", hit_branch["entry_index"], "entry_index/I")
    hit_tree.Branch("tube_id", hit_branch["tube_id"])
    hit_tree.Branch("charge", hit_branch["charge"])
    hit_tree.Branch("time", hit_branch["time"])

    handles = {
        "event_tree": event_tree,
        "hit_tree": hit_tree,
        "event_branch": event_branch,
        "hit_branch": hit_branch,
    }

    return handles


def fill_event_and_hit_trees(handles, entry_index, merged, positron_trk):
    """
    Fill one event in EventSummary and PmtHitMap.
    """

    event_tree = handles["event_tree"]
    hit_tree = handles["hit_tree"]
    event_branch = handles["event_branch"]
    hit_branch = handles["hit_branch"]

    # Basic event scalars
    event_branch["entry_index"][0] = int(entry_index)
    event_branch["n_triggers"][0] = int(merged["n_triggers"])
    event_branch["n_raw_hits"][0] = int(merged["n_raw_hits"])
    event_branch["n_digi_hits"][0] = int(merged["n_digi_hits"])
    event_branch["n_raw_tubes_hit_sum"][0] = int(merged["n_raw_tubes_hit_sum"])
    event_branch["n_digi_tubes_hit_sum"][0] = int(merged["n_digi_tubes_hit_sum"])
    event_branch["n_digi_tubes_hit_merged"][0] = int(merged["n_digi_tubes_hit_merged"])
    event_branch["tot_charge"][0] = float(merged["tot_charge"])
    event_branch["min_time"][0] = float(merged["min_time"])
    event_branch["max_time"][0] = float(merged["max_time"])

    # Electron/Positron information
    start = np.asarray(positron_trk["start"], dtype=float)
    stop = np.asarray(positron_trk["stop"], dtype=float)
    direction = np.asarray(positron_trk["direction"], dtype=float)
    event_branch["energy_MeV"][0] = float(positron_trk["K"])
    event_branch["track_length_cm"][0] = float(np.linalg.norm(stop - start))
    event_branch["true_p"][0] = float(positron_trk["p"])
    event_branch["true_E"][0] = float(positron_trk["E"])
    event_branch["true_K"][0] = float(positron_trk["K"])
    event_branch["true_M"][0] = float(positron_trk["M"])
    event_branch["true_time"][0] = float(positron_trk["time"])
    event_branch["true_ipnu"][0] = int(positron_trk["ipnu"])
    event_branch["true_parent_type"][0] = int(positron_trk["parent_type"])
    for i in range(3):
        event_branch["true_start"][i] = float(start[i])
        event_branch["true_stop"][i] = float(stop[i])
        event_branch["true_dir"][i] = float(direction[i])

    event_tree.Fill()

    # Hit map
    hit_branch["entry_index"][0] = int(entry_index)

    hit_branch["tube_id"].clear()
    hit_branch["charge"].clear()
    hit_branch["time"].clear()

    charge_by_tube = merged["charge_by_tube"]
    time_by_tube = merged["time_by_tube"]

    for tube_id in sorted(charge_by_tube):
        hit_branch["tube_id"].push_back(int(tube_id))
        hit_branch["charge"].push_back(float(charge_by_tube[tube_id]))
        hit_branch["time"].push_back(float(time_by_tube[tube_id]))

    hit_tree.Fill()


def make_summary_root(input_file, output_file):
    load_wcsim_library()

    input_root = ROOT.TFile.Open(str(input_file))
    if not input_root or input_root.IsZombie():
        raise RuntimeError(f"Could not open input file: {input_file}")

    wcsim_tree = input_root.Get("wcsimT")
    if not wcsim_tree:
        raise RuntimeError("Could not find tree 'wcsimT' in input file.")

    output_root = ROOT.TFile(str(output_file), "RECREATE")
    if not output_root or output_root.IsZombie():
        raise RuntimeError(f"Could not create output file: {output_file}")

    # Geometry tree, copied once
    fill_geometry_tree(input_root, output_root)

    # EventSummary and PmtHitMap trees
    handles = create_output_trees(output_root)

    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    n_entries = int(wcsim_tree.GetEntries())
    print(f"Input WCSim entries: {n_entries}")

    n_no_positron = 0
    n_multi_trigger = 0

    for entry_index in range(n_entries):
        wcsim_tree.GetEntry(entry_index)

        merged = merge_trigger_hits_from_event(event)

        if merged["n_triggers"] > 1:
            n_multi_trigger += 1

        tracks = merged["first_trigger_tracks"]
        positron_trk = None

        if tracks is not None:
            positron_trk = find_primary_positron_track(tracks, entry_index)

        if positron_trk is None:
            n_no_positron += 1

        fill_event_and_hit_trees(
            handles=handles,
            entry_index=entry_index,
            merged=merged,
            positron_trk=positron_trk,
        )

        if (entry_index + 1) % 1000 == 0:
            print(f"Processed {entry_index + 1}/{n_entries} events")

    output_root.cd()
    handles["event_tree"].Write()
    handles["hit_tree"].Write()

    output_root.Close()
    input_root.Close()

    print()
    print(f"Saved summary ROOT file: {output_file}")
    if n_no_positron > 0:
        print(f"Events without unique primary positron: {n_no_positron}")
    if n_multi_trigger > 0:
        print(f"Events with more than one WCSim trigger object: {n_multi_trigger}")


def default_output_path(input_file):
    input_path = Path(input_file)

    if input_path.suffix == ".root":
        return input_path.with_name(input_path.stem + "_summary.root")

    return input_path.with_name(input_path.name + "_summary.root")


def main():
    parser = argparse.ArgumentParser(
        description="Create compact ROOT summary from fixed-energy positron WCSim file."
    )

    parser.add_argument(
        "--input_file",
        type=str,
        help="Input WCSim ROOT file.",
    )

    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help="Output summary ROOT file. Default: input_summary.root.",
    )

    args = parser.parse_args()

    input_file = Path(args.input_file)

    if args.output_file is None:
        output_file = default_output_path(input_file)
    else:
        output_file = Path(args.output_file)

    make_summary_root(input_file, output_file)


if __name__ == "__main__":
    main()
