import argparse
from pathlib import Path

import numpy as np  # type: ignore
import ROOT  # type: ignore


def load_wcsim_library() -> None:
    """
    Load the WCSim ROOT dictionary.

    This requires that the WCSim environment has already been sourced,
    e.g. this_wcsim.sh or the corresponding container setup script.
    """
    status = ROOT.gSystem.Load("libWCSimRoot.so")

    if status < 0:
        raise RuntimeError(
            "Could not load libWCSimRoot.so. "
            "Make sure the WCSim environment is sourced inside the container."
        )


def load_trees(input_path: Path):
    """
    Open a WCSim ROOT file and retrieve the main event tree.

    Args:
        input_path: Path to the input ROOT file.

    Returns:
        Tuple containing the WCSim event tree and the input ROOT file.
    """
    input_root = ROOT.TFile.Open(str(input_path), "READ")

    if not input_root or input_root.IsZombie():
        raise RuntimeError(f"Could not open input ROOT file: {input_path}")

    wcsim_tree = input_root.Get("wcsimT")

    if not wcsim_tree:
        input_root.Close()
        raise RuntimeError("Could not find tree 'wcsimT' in the input file.")

    return wcsim_tree, input_root


def copy_tree(input_root, output_root, tree_name: str) -> None:
    """
    Copy a complete TTree from the input ROOT file to the output ROOT file.

    Args:
        input_root: Input ROOT file.
        output_root: Output ROOT file.
        tree_name: Name of the tree to copy.
    """
    tree = input_root.Get(tree_name)

    if not tree:
        raise RuntimeError(f"Could not find tree '{tree_name}' in the input file.")

    output_root.cd()
    tree.CloneTree(-1, "fast").Write()


def filter_tracks(trigger):
    """
    Check whether the trigger contains the expected muon and decay electron/positron.

    All WCSim truth tracks are stored in trigger 0.

    Args:
        trigger: WCSimRootTrigger containing the truth tracks.

    Returns:
        Tuple (find_muon, find_electron).
    """
    n_tracks = trigger.GetNtrack()
    true_tracks = trigger.GetTracks()

    find_muon = False
    find_electron = False

    for i_track in range(n_tracks):
        track = true_tracks.At(i_track)

        ipnu = int(track.GetIpnu())
        parent_type = int(track.GetParenttype())

        start = np.array(
            [
                float(track.GetStart(0)),
                float(track.GetStart(1)),
                float(track.GetStart(2)),
            ]
        )

        # Look for the primary muon.
        if abs(ipnu) == 13 and parent_type == 0:
            find_muon = True

            stop_muon = np.array(
                [
                    float(track.GetStop(0)),
                    float(track.GetStop(1)),
                    float(track.GetStop(2)),
                ]
            )

        # Look for an electron/positron produced by the muon decay
        # at the muon stopping point.
        if (
            abs(ipnu) == 11
            and abs(parent_type) == 13
            and np.allclose(start, stop_muon, rtol=0.0, atol=1e-6)
        ):
            find_electron = True

    return find_muon, find_electron


def check_event(event, n_events, i_entry, output_tree):
    """
    Check whether a WCSim event satisfies the required selection.

    If the event passes the selection, copy it to the output tree.

    Args:
        event: WCSimRootEvent.
        n_events: Current number of accepted events.
        i_entry: Entry index in the input tree.
        output_tree: Output tree where accepted events are stored.

    Returns:
        Updated number of accepted events.
    """
    for i_trigger in range(event.GetNumberOfEvents()):
        trigger = event.GetTrigger(i_trigger)

        n_digi_hits = trigger.GetNcherenkovdigihits()

        if n_digi_hits <= 0:
            print(
                f"Event {i_entry}, trigger {i_trigger} rejected: no digitized hits.\n"
            )
            return n_events

    trigger = event.GetTrigger(0)
    find_muon, find_electron = filter_tracks(trigger)

    if not (find_muon and find_electron):
        print(
            f"Event {i_entry} rejected: "
            f"muon found: {find_muon}, "
            f"electron found: {find_electron}.\n"
        )
        return n_events

    output_tree.Fill()
    n_events += 1

    return n_events


def main(input_file: str) -> None:
    load_wcsim_library()

    input_path = Path(input_file)

    wcsim_tree, input_root = load_trees(input_path)

    output_path_1trigg = input_path.with_name(
        f"{input_path.stem}_1trigg{input_path.suffix}"
    )
    output_path_2trigg = input_path.with_name(
        f"{input_path.stem}_2trigg{input_path.suffix}"
    )

    output_root_1trigg = ROOT.TFile.Open(
        str(output_path_1trigg),
        "RECREATE",
    )

    output_root_2trigg = ROOT.TFile.Open(
        str(output_path_2trigg),
        "RECREATE",
    )

    # Prepare the WCSim event branch.
    event = ROOT.WCSimRootEvent()

    wcsim_tree.SetBranchAddress(
        "wcsimrootevent",
        ROOT.AddressOf(event),
    )

    # ------------------------------------------------------------------
    # Prepare output file for events with one trigger.
    # ------------------------------------------------------------------

    output_root_1trigg.cd()

    # Clone only the structure of the event tree.
    output_tree_1trigg = wcsim_tree.CloneTree(0)

    # Copy geometry and WCSim configuration unchanged.
    copy_tree(
        input_root,
        output_root_1trigg,
        "wcsimGeoT",
    )

    copy_tree(
        input_root,
        output_root_1trigg,
        "wcsimRootOptionsT",
    )

    # ------------------------------------------------------------------
    # Prepare output file for events with two triggers.
    # ------------------------------------------------------------------

    output_root_2trigg.cd()

    # Clone only the structure of the event tree.
    output_tree_2trigg = wcsim_tree.CloneTree(0)

    # Copy geometry and WCSim configuration unchanged.
    copy_tree(
        input_root,
        output_root_2trigg,
        "wcsimGeoT",
    )

    copy_tree(
        input_root,
        output_root_2trigg,
        "wcsimRootOptionsT",
    )

    # ------------------------------------------------------------------
    # Event loop.
    # ------------------------------------------------------------------

    n_entries = wcsim_tree.GetEntries()

    n_events_1trigg = 0
    n_events_2trigg = 0

    for i_entry in range(n_entries):
        wcsim_tree.GetEntry(i_entry)

        n_triggers = event.GetNumberOfEvents()

        if n_triggers == 1:
            n_events_1trigg = check_event(
                event,
                n_events_1trigg,
                i_entry,
                output_tree_1trigg,
            )

        elif n_triggers == 2:
            n_events_2trigg = check_event(
                event,
                n_events_2trigg,
                i_entry,
                output_tree_2trigg,
            )

        else:
            print("=" * 80)
            print(f"WARNING: Event {i_entry} has {n_triggers} triggers, skipping.\n")
            print("=" * 80)

    # ------------------------------------------------------------------
    # Summary.
    # ------------------------------------------------------------------

    print(f"Total events with 1 trigger: {n_events_1trigg} out of {n_entries}.")

    print(f"Total events with 2 triggers: {n_events_2trigg} out of {n_entries}.")

    # ------------------------------------------------------------------
    # Write the filtered event trees and close the files.
    # Geometry and options trees have already been written by copy_tree().
    # ------------------------------------------------------------------

    output_root_1trigg.cd()
    output_tree_1trigg.Write()
    output_root_1trigg.Close()

    output_root_2trigg.cd()
    output_tree_2trigg.Write()
    output_root_2trigg.Close()

    input_root.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=("Filter a WCSim ROOT file into events with one or two triggers.")
    )

    parser.add_argument(
        "input_file",
        help="Path to the input WCSim ROOT file.",
    )

    args = parser.parse_args()

    main(args.input_file)
