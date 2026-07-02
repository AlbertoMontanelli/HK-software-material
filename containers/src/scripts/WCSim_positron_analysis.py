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
import gzip
import pickle

import numpy as np
import ROOT  # type: ignore


def get_hits(trigger):

    n_raw_hits = int(trigger.GetNcherenkovhits())
    n_digi_hits = int(trigger.GetNcherenkovdigihits())
    n_raw_tubes_hit = int(trigger.GetNumTubesHit())
    n_digi_tubes_hit = int(trigger.GetNumDigiTubesHit())
    digi_hits = trigger.GetCherenkovDigiHits()
    charge_by_tube = {}
    time_by_tube = {}

    for i in range(n_digi_hits):
        hit = digi_hits.At(i)

        tube_id = int(hit.GetTubeId())
        charge = float(hit.GetQ())
        time = float(hit.GetT())

        charge_by_tube[tube_id] = charge
        time_by_tube[tube_id] = time

    tot_charge = sum(charge_by_tube.values())
    min_time = min(time_by_tube.values()) if time_by_tube else None
    max_time = max(time_by_tube.values()) if time_by_tube else None

    return {
        "charge_by_tube": charge_by_tube,
        "time_by_tube": time_by_tube,
        "n_raw_hits": n_raw_hits,
        "n_digi_hits": n_digi_hits,
        "tot_charge": tot_charge,
        "min_time": min_time,
        "max_time": max_time,
        "n_raw_tubes_hit": n_raw_tubes_hit,
        "n_digi_tubes_hit": n_digi_tubes_hit,
    }


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
                "ipnu": trk.GetIpnu(),
                "parent_type": trk.GetParenttype(),
                "creator": trk.GetCreatorProcessName(),
                "start": start,
                "stop": stop,
                "direction": direction,
                "M": float(trk.GetM()),
                "p": float(trk.GetP()),
                "E": float(trk.GetE()),
                "K": float(trk.GetE()) - float(trk.GetM()),
                "time": float(trk.GetTime()),
            }
        )

    return tracks


def positron_track(tracks, event_index):
    """Find the primary generated positron track."""
    candidates = []

    for trk in tracks:
        if (
            abs(trk["ipnu"]) == 11
            and trk["parent_type"] == 0
            and trk["M"] > 0
            and trk["creator"] == "initial"
        ):
            candidates.append(trk)

    if len(candidates) != 1:
        print(
            f"WARNING: found {len(candidates)} candidate positron tracks "
            f"at event: {event_index}, expected 1."
        )
        return None

    positron_trk = candidates[0]

    return positron_trk


def trigger_info(trigger):
    trigger_type = int(trigger.GetTriggerType())
    trigger_info_size = int(trigger.GetTriggerInfo().size())
    return trigger_type, trigger_info_size


def get_summary(input_file):
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

    summary = []

    for entry_index in range(n_entries):
        wcsim_tree.GetEntry(entry_index)

        n_triggers = int(event.GetNumberOfEvents())

        entry_summary = {
            "entry_index": entry_index,
            "positron_track": None,
            "triggers": [],
        }

        for trigger_index in range(n_triggers):
            trigger = event.GetTrigger(trigger_index)

            tracks = get_tracks(trigger)

            if trigger_index == 0:
                entry_summary["positron_track"] = positron_track(tracks, entry_index)

            trigger_summary = {
                "trigger_index": trigger_index,
                "hits": get_hits(trigger),
            }

            entry_summary["triggers"].append(trigger_summary)

        summary.append(entry_summary)

        return summary


def main(input_file):
    output_path = str(input_file).replace(".root", "_summary.pkl.gz")
    summary = get_summary(str(input_file))

    with gzip.open(output_path, "wb") as f:
        pickle.dump(summary, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Saved summary to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize fixed-energy positron WCSim samples into a ROOT TTree."
    )
    parser.add_argument("input_file", type=str, help="Path to the input ROOT file.")
    args = parser.parse_args()

    main(args.input_file)
