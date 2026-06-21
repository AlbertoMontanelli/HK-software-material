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
                "p": float(trk.GetP()),
                "E": float(trk.GetE()),
                "time": float(trk.GetTime()),
            }
        )

    return tracks


def main(path, event_index=None):
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

        for itrigger in range(event.GetNumberOfEvents()):
            trigger = event.GetTrigger(itrigger)

            print("trigger", itrigger)
            print("trigger type:", trigger.GetTriggerType())
            print("n digitized hits:", trigger.GetNcherenkovdigihits())
            print("sum Q:", trigger.GetSumQ())

            tracks = extract_true_tracks(trigger)
            print("\nTrue tracks information:")
            for i in range(len(tracks)):
                dict_track = tracks[i]
                if dict_track["parent_type"] in (0, -13):
                    print(
                        f"Track {i}: ipnu={dict_track['ipnu']}, "
                        f"parent_type={dict_track['parent_type']}, "
                        f"start={dict_track['start']}, stop={dict_track['stop']}, "
                        f"direction={dict_track['direction']}, p={dict_track['p']}, "
                        f"E={dict_track['E']}, time={dict_track['time']}\n"
                    )


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

    args = parser.parse_args()
    main(args.input_file, event_index=args.event_index)
