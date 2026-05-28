import argparse
from pathlib import Path

import ROOT  # type: ignore


def collect_mc_tracks(event, trigger_index=0):
    """
    Collect MC truth tracks from a WCSim event trigger.

    Returns a list of dictionaries with approximate truth information.
    Method names can vary slightly with the WCSim version, so this may need
    minor adjustment after inspecting the object with dir(track).
    """
    trigger = event.GetTrigger(trigger_index)

    n_tracks = int(trigger.GetNtrack())
    tracks = trigger.GetTracks()

    output = []

    for i in range(n_tracks):
        track = tracks.At(i)

        info = {
            "index": i,
            "pdg": int(track.GetIpnu()),
            "start_x": float(track.GetStart(0)),
            "start_y": float(track.GetStart(1)),
            "start_z": float(track.GetStart(2)),
            "stop_x": float(track.GetStop(0)),
            "stop_y": float(track.GetStop(1)),
            "stop_z": float(track.GetStop(2)),
            "dir_x": float(track.GetDir(0)),
            "dir_y": float(track.GetDir(1)),
            "dir_z": float(track.GetDir(2)),
            "energy": float(track.GetE()),
            "mass": float(track.GetM()),
            "parent_type": int(track.GetParenttype()),
        }

        output.append(info)

    return output


def main(path, event_index=None):
    ROOT.gSystem.Load("libWCSimRoot.so")

    root_file = ROOT.TFile.Open(str(path))

    geo_tree = root_file.Get("wcsimGeoT")
    geo_tree.GetEntry(0)

    geom = ROOT.WCSimRootGeom()
    geom_branch = geo_tree.GetBranch("wcsimrootgeom")
    geom_branch.SetAddress(ROOT.AddressOf(geom))

    event_tree = root_file.Get("wcsimT")
    n_entries = event_tree.GetEntries()

    if event_index is None:
        event_indices = range(n_entries)
    else:
        event_indices = [event_index]

    event = ROOT.WCSimRootEvent()
    event_branch = event_tree.GetBranch("wcsimrootevent")
    event_branch.SetAddress(ROOT.AddressOf(event))

    for event_index in event_indices:
        event_tree.GetEntry(event_index)

        print(f"\nEntry {event_index}")
        print("Number of triggers:", event.GetNumberOfEvents())
        print("Has subevents:", event.HasSubEvents())

        for itrigger in range(event.GetNumberOfEvents()):
            trigger = event.GetTrigger(itrigger)

            print("trigger", itrigger)
            print("trigger type:", trigger.GetTriggerType())
            print("n digitized hits:", trigger.GetNcherenkovdigihits())
            print("sum Q:", trigger.GetSumQ())

            times = []
            digi_hits = trigger.GetCherenkovDigiHits()

            for i in range(trigger.GetNcherenkovdigihits()):
                hit = digi_hits.At(i)
                times.append(hit.GetT())

            if times:
                print("  t min:", min(times))
                print("  t max:", max(times))

            n_tracks = int(trigger.GetNtrack())
            tracks = trigger.GetTracks()

            for i in range(n_tracks):
                track = tracks.At(i)

                info = {
                    "index": i,
                    "pdg": int(track.GetIpnu()),
                    "start_x": float(track.GetStart(0)),
                    "start_y": float(track.GetStart(1)),
                    "start_z": float(track.GetStart(2)),
                    "stop_x": float(track.GetStop(0)),
                    "stop_y": float(track.GetStop(1)),
                    "stop_z": float(track.GetStop(2)),
                    "dir_x": float(track.GetDir(0)),
                    "dir_y": float(track.GetDir(1)),
                    "dir_z": float(track.GetDir(2)),
                    "energy": float(track.GetE()),
                    "mass": float(track.GetM()),
                    "parent_type": int(track.GetParenttype()),
                }

                print(info)


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
