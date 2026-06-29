#!/usr/bin/env python3
"""
Summarize fixed-energy positron WCSim samples into a flat ROOT TTree.

The script assumes that the input ROOT file was produced in consecutive
energy blocks, e.g.

    /gun/energy 0.3 MeV ; /run/beamOn 1000
    /gun/energy 1.0 MeV ; /run/beamOn 1000
    ...

It produces:
  - one ROOT file with a flat TTree called "event_summary".

Run inside the WCSimRootPyROOT container.
"""

import argparse
from array import array

import numpy as np
import ROOT  # type: ignore


def get_nominal_energy(event_index):
    """Return the nominal gun energy from the event index."""
    energy_blocks = [
        (0, 999, 0.3),
        (1000, 1999, 1.0),
        (2000, 2999, 10.0),
        (3000, 3999, 20.0),
        (4000, 4999, 38.0),
        (5000, 5999, 50.0),
    ]

    for start, stop, energy in energy_blocks:
        if start <= event_index <= stop:
            return energy

    raise ValueError(f"Event index {event_index} is not in any known energy block.")


def get_digi_hits(trigger):
    """Return digitized PMT charge and time from a WCSim trigger."""
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


def track_info(trigger):
    """Return a list of dictionaries with true particle information."""
    tracks = []

    n_tracks = int(trigger.GetNtrack())
    true_tracks = trigger.GetTracks()

    for i in range(n_tracks):
        trk = true_tracks.At(i)

        ipnu = int(trk.GetIpnu())
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


def positron_track(tracks, event_index):
    """Find the primary generated positron track."""
    candidates = []

    for trk in tracks:
        if trk["ipnu"] == -11 and trk["parent_type"] == 0 and trk["E"] > trk["p"]:
            candidates.append(trk)

    if len(candidates) != 1:
        print(
            f"WARNING: found {len(candidates)} candidate positron tracks "
            f"at event: {event_index}, expected 1."
        )

    if len(candidates) == 0:
        return None

    trk = candidates[0]

    p = trk["p"]
    En = trk["E"]
    start = trk["start"]
    stop = trk["stop"]
    length = float(np.linalg.norm(stop - start))

    return p, En, length, start, stop


def create_output_tree(output_file_name):
    """
    Create the output ROOT file and flat TTree.

    Returns:
        output_file, output_tree, branches

    where branches is a dictionary of one-element arrays.
    """
    output_file = ROOT.TFile(str(output_file_name), "RECREATE")
    output_tree = ROOT.TTree(
        "event_summary",
        "Flat summary of fixed-energy positron WCSim events",
    )

    branches = {
        "event_index": array("i", [0]),
        "nominal_energy_mev": array("f", [0.0]),
        # WCSim event/trigger object information.
        "n_wcsim_trigger_objects": array("i", [0]),
        "has_single_wcsim_trigger_object": array("i", [0]),
        # Raw / pre-digitization Cherenkov information.
        "n_raw_hits": array("i", [0]),
        "n_raw_hit_times": array("i", [0]),
        "n_raw_tubes_hit": array("i", [0]),
        # Digitized detector information.
        "n_digi_hits": array("i", [0]),
        "n_digi_tubes_hit": array("i", [0]),
        "total_charge_pe": array("f", [0.0]),
        "first_hit_time_ns": array("f", [np.nan]),
        "last_hit_time_ns": array("f", [np.nan]),
        # Trigger information.
        "trigger_type": array("i", [-999]),
        "trigger_info_size": array("i", [0]),
        # Boolean analysis flags.
        "has_raw_light": array("i", [0]),
        "has_digi_hits": array("i", [0]),
        "has_valid_trigger": array("i", [0]),
        # Truth positron information.
        "true_p_mev": array("f", [np.nan]),
        "true_E_mev": array("f", [np.nan]),
        "track_length_cm": array("f", [np.nan]),
        "true_positron_start_x_cm": array("f", [np.nan]),
        "true_positron_start_y_cm": array("f", [np.nan]),
        "true_positron_start_z_cm": array("f", [np.nan]),
        "true_positron_stop_x_cm": array("f", [np.nan]),
        "true_positron_stop_y_cm": array("f", [np.nan]),
        "true_positron_stop_z_cm": array("f", [np.nan]),
    }

    # ROOT branch type codes:
    # I = integer
    # F = float
    branch_types = {
        "event_index": "I",
        "nominal_energy_mev": "F",
        "n_wcsim_trigger_objects": "I",
        "has_single_wcsim_trigger_object": "I",
        "n_raw_hits": "I",
        "n_raw_hit_times": "I",
        "n_raw_tubes_hit": "I",
        "n_digi_hits": "I",
        "n_digi_tubes_hit": "I",
        "total_charge_pe": "F",
        "first_hit_time_ns": "F",
        "last_hit_time_ns": "F",
        "trigger_type": "I",
        "trigger_info_size": "I",
        "has_raw_light": "I",
        "has_digi_hits": "I",
        "has_valid_trigger": "I",
        "true_p_mev": "F",
        "true_E_mev": "F",
        "track_length_cm": "F",
        "true_positron_start_x_cm": "F",
        "true_positron_start_y_cm": "F",
        "true_positron_start_z_cm": "F",
        "true_positron_stop_x_cm": "F",
        "true_positron_stop_y_cm": "F",
        "true_positron_stop_z_cm": "F",
    }
    # Create branches in the TTree for each observable. For each
    # branch, pass the name, the address where the value is stored and
    # read by ROOT, and the branch type code. ``arr`` should be an
    # object with the same memory address for every event, only the
    # value at that address changes.
    for name, arr in branches.items():
        output_tree.Branch(name, arr, f"{name}/{branch_types[name]}")

    return output_file, output_tree, branches


def reset_branches(branches):
    """Reset all branch values to default values before filling one event."""
    branches["event_index"][0] = -1
    branches["nominal_energy_mev"][0] = np.nan

    branches["n_wcsim_trigger_objects"][0] = 0
    branches["has_single_wcsim_trigger_object"][0] = 0

    branches["n_raw_hits"][0] = 0
    branches["n_raw_hit_times"][0] = 0
    branches["n_raw_tubes_hit"][0] = 0

    branches["n_digi_hits"][0] = 0
    branches["n_digi_tubes_hit"][0] = 0
    branches["total_charge_pe"][0] = 0.0
    branches["first_hit_time_ns"][0] = np.nan
    branches["last_hit_time_ns"][0] = np.nan

    branches["trigger_type"][0] = -999
    branches["trigger_info_size"][0] = 0

    branches["has_raw_light"][0] = 0
    branches["has_digi_hits"][0] = 0
    branches["has_valid_trigger"][0] = 0

    branches["true_p_mev"][0] = np.nan
    branches["true_E_mev"][0] = np.nan
    branches["track_length_cm"][0] = np.nan

    branches["true_positron_start_x_cm"][0] = np.nan
    branches["true_positron_start_y_cm"][0] = np.nan
    branches["true_positron_start_z_cm"][0] = np.nan

    branches["true_positron_stop_x_cm"][0] = np.nan
    branches["true_positron_stop_y_cm"][0] = np.nan
    branches["true_positron_stop_z_cm"][0] = np.nan


def fill_basic_event_info(
    branches, event_index, nominal_energy, n_wcsim_trigger_objects
):
    """Fill event-level information that exists for every generated event."""
    branches["event_index"][0] = event_index
    branches["nominal_energy_mev"][0] = nominal_energy

    branches["n_wcsim_trigger_objects"][0] = n_wcsim_trigger_objects
    branches["has_single_wcsim_trigger_object"][0] = int(n_wcsim_trigger_objects == 1)


def fill_raw_and_trigger_info(branches, trigger):
    """Fill raw Cherenkov-hit and trigger metadata."""
    n_raw_hits = int(trigger.GetNcherenkovhits())
    n_raw_hit_times = int(trigger.GetNcherenkovhittimes())
    n_raw_tubes_hit = int(trigger.GetNumTubesHit())

    trigger_type = int(trigger.GetTriggerType())
    trigger_info_size = int(trigger.GetTriggerInfo().size())

    branches["n_raw_hits"][0] = n_raw_hits
    branches["n_raw_hit_times"][0] = n_raw_hit_times
    branches["n_raw_tubes_hit"][0] = n_raw_tubes_hit

    branches["trigger_type"][0] = trigger_type
    branches["trigger_info_size"][0] = trigger_info_size

    branches["has_raw_light"][0] = int(n_raw_hits > 0)


def fill_detector_info(branches, trigger):
    """Fill detector-level observables from digitized PMT hits."""
    charge_by_tube, time_by_tube = get_digi_hits(trigger)

    n_digi_hits = int(trigger.GetNcherenkovdigihits())

    branches["n_digi_hits"][0] = n_digi_hits
    branches["has_digi_hits"][0] = int(n_digi_hits > 0)

    if n_digi_hits <= 0:
        return

    branches["n_digi_tubes_hit"][0] = int(trigger.GetNumDigiTubesHit())
    branches["n_digi_hits"][0] = n_digi_hits
    branches["total_charge_pe"][0] = sum(charge_by_tube.values())

    if len(time_by_tube) > 0:
        branches["first_hit_time_ns"][0] = min(time_by_tube.values())
        branches["last_hit_time_ns"][0] = max(time_by_tube.values())


def fill_truth_info(branches, trigger, event_index):
    """Fill true positron information from WCSim true tracks."""
    tracks = track_info(trigger)
    positron = positron_track(tracks, event_index)

    if positron is None:
        return

    p, En, length, start, stop = positron

    branches["true_p_mev"][0] = p
    branches["true_E_mev"][0] = En
    branches["track_length_cm"][0] = length

    branches["true_positron_start_x_cm"][0] = start[0]
    branches["true_positron_start_y_cm"][0] = start[1]
    branches["true_positron_start_z_cm"][0] = start[2]

    branches["true_positron_stop_x_cm"][0] = stop[0]
    branches["true_positron_stop_y_cm"][0] = stop[1]
    branches["true_positron_stop_z_cm"][0] = stop[2]


def update_analysis_flags(branches):
    """Set final analysis flags after raw and digi information has been filled."""
    trigger_type = branches["trigger_type"][0]
    n_digi_hits = branches["n_digi_hits"][0]

    branches["has_digi_hits"][0] = int(n_digi_hits > 0)
    branches["has_valid_trigger"][0] = int(trigger_type >= 0 and n_digi_hits > 0)


def main(input_file):
    ROOT.gSystem.Load("libWCSimRoot.so")

    root_file = ROOT.TFile.Open(str(input_file))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open input file: {input_file}")

    wcsim_tree = root_file.Get("wcsimT")
    if not wcsim_tree:
        raise RuntimeError("Could not find tree 'wcsimT' in input file.")

    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    n_entries = int(wcsim_tree.GetEntries())
    print(f"Input entries: {n_entries}")

    path = str(input_file).replace(".root", "_summary.root")
    output_file, output_tree, branches = create_output_tree(path)

    for event_index in range(n_entries):
        wcsim_tree.GetEntry(event_index)

        reset_branches(branches)

        nominal_energy = get_nominal_energy(event_index)
        n_wcsim_trigger_objects = int(event.GetNumberOfEvents())

        fill_basic_event_info(
            branches=branches,
            event_index=event_index,
            nominal_energy=nominal_energy,
            n_wcsim_trigger_objects=n_wcsim_trigger_objects,
        )

        if n_wcsim_trigger_objects == 0:
            print(f"Entry {event_index} has no WCSim trigger objects.")

        elif n_wcsim_trigger_objects > 1:
            print(
                f"Entry {event_index} has "
                f"{n_wcsim_trigger_objects} WCSim trigger objects."
            )

            # For now, fill only object-level information from the first one.
            # Later we can loop over all subevents if needed.
            trigger = event.GetTrigger(0)

            fill_raw_and_trigger_info(branches, trigger)
            fill_detector_info(branches, trigger)
            update_analysis_flags(branches)

            if branches["has_valid_trigger"][0] == 1:
                fill_truth_info(branches, trigger, event_index)

        else:
            trigger = event.GetTrigger(0)

            fill_raw_and_trigger_info(branches, trigger)
            fill_detector_info(branches, trigger)
            update_analysis_flags(branches)

            if branches["has_valid_trigger"][0] == 1:
                fill_truth_info(branches, trigger, event_index)

        output_tree.Fill()

        event.ReInitialize()

    output_file.cd()
    output_tree.Write()
    output_file.Close()
    root_file.Close()

    print(f"Saved flat summary tree to: {path}")
    print("Tree name: event_summary")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize fixed-energy positron WCSim samples into a ROOT TTree."
    )
    parser.add_argument("input_file", type=str, help="Path to the input ROOT file.")
    args = parser.parse_args()

    main(args.input_file)
