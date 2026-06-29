import argparse
from pathlib import Path

import numpy as np
import ROOT  # type: ignore


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
                "M": float(trk.GetM()),
                "p": float(trk.GetP()),
                "E": float(trk.GetE()),
                "time": float(trk.GetTime()),
                "id": int(trk.GetId()),
                "parent_id": int(trk.GetParentId()),
                "creator": trk.GetCreatorProcessName(),
            }
        )

    return tracks


def print_track_info(dict_track, i):
    print(
        f"Track {i}: "
        f"Geant4_id = {dict_track['id']}, "
        f"parent_id = {dict_track['parent_id']}, "
        f"PDG_id = {dict_track['ipnu']}, "
        f"parent_type = {dict_track['parent_type']}, "
        f"creator = {dict_track['creator']}, "
        f"p = {dict_track['p']}, "
        f"M = {dict_track['M']}, "
        f"E = {dict_track['E']}, "
        f"K = {dict_track['E'] - dict_track['M']}, "
        f"time = {dict_track['time']}, "
        f"start = {dict_track['start']}, stop = {dict_track['stop']}\n"
    )


def main(path, event_index=None, full_tracks=False):
    ROOT.gSystem.Load("libWCSimRoot.so")
    root_file = ROOT.TFile.Open(str(path))

    wcsim_tree = root_file.Get("wcsimT")
    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    geo_tree = root_file.Get("wcsimGeoT")
    geom = ROOT.WCSimRootGeom()
    geo_tree.SetBranchAddress("wcsimrootgeom", ROOT.AddressOf(geom))

    n_entries = wcsim_tree.GetEntries()

    if event_index is None:
        event_indices = range(n_entries)
    else:
        event_indices = [event_index]

    for event_index in event_indices:
        wcsim_tree.GetEntry(event_index)

        print(f"\nEntry {event_index}")
        print("Number of triggers:", event.GetNumberOfEvents())
        print("Has subevents:", event.HasSubEvents())

        # una sola volta per entry
        truth_trigger = event.GetTrigger(0)
        tracks = extract_true_tracks(truth_trigger)

        print("\nTrue tracks information from trigger 0:")
        for i, dict_track in enumerate(tracks):
            if full_tracks or dict_track["parent_type"] in (0, -13):
                print_track_info(dict_track, i)

        print("=" * 80)
        print("Trigger information for all triggers in this entry:")
        for itrigger in range(event.GetNumberOfEvents()):
            trigger = event.GetTrigger(itrigger)

            print("trigger", itrigger)
            print("trigger type:", trigger.GetTriggerType())
            print("n tracks stored in this trigger:", trigger.GetNtrack())
            print("n digitized hits:", trigger.GetNcherenkovdigihits())
            print("sum Q:", trigger.GetSumQ())
            print("*" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count triggers and digitized hits in a WCSim ROOT file."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input WCSim ROOT file.",
    )
    parser.add_argument(
        "--event_index",
        type=int,
        default=None,
        help="Index of the event to analyze. If omitted, all entries are analyzed.",
    )
    parser.add_argument(
        "--full_tracks",
        action="store_true",
        help="Print all tracks, including those with parent_type not equal to 0 or -13.",
    )
    args = parser.parse_args()
    main(args.input_file, event_index=args.event_index, full_tracks=args.full_tracks)
