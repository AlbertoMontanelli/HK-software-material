#!/usr/bin/env python3

import argparse

import numpy as np

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
    
def load_trees(input_file):
    """
    Load WCSim trees from a ROOT file.

    Args:
        input_file: Path to the input ROOT file.
    Returns:
        A tuple containing the WCSim event tree and the ROOT file object.
    """
    input_root = ROOT.TFile.Open(str(input_file), "READ")
    wcsim_tree = input_root.Get("wcsimT")
    return wcsim_tree, input_root


def copy_tree(input_file, output_file, tree_name: str) -> None:
    tree = input_file.Get(tree_name)
    output_file.cd()
    tree.CloneTree(-1, "fast").Write()

def filter_tracks(trigger):
    """
    Filter tracks in a WCSim trigger based on specific criteria.

    Args:
        trigger: The WCSim trigger to filter tracks from.
    """
    n_tracks = trigger.GetNtrack()
    true_tracks = trigger.GetTracks()
    find_muon = False
    find_electron = False

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
        if abs(ipnu) == 13 and parent_type == 0:
            find_muon = True
            stop_muon = np.array(
                [
                    float(trk.GetStop(0)),
                    float(trk.GetStop(1)),
                    float(trk.GetStop(2)),
                ]
            )
        if abs(ipnu) == 11 and abs(parent_type) == 13 and start.all()==stop_muon.all():
            find_electron = True
    return find_muon, find_electron

def main(input_file):
    load_wcsim_library()
    wcsim_tree, input_root = load_trees(input_file)
    output_root = ROOT.TFile.Open(str(input_file).replace(".root", "_filtered.root"), "RECREATE")

    # Copy geometry/options trees.
    for aux_tree_name in [
        "wcsimGeoT",
        "wcsimRootOptionsT",
    ]:
        copy_tree(input_root, output_root, aux_tree_name)

    # Prepare input branch.
    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    # Clone the event tree structure, initially empty.
    output_root.cd()
    output_tree = wcsim_tree.CloneTree(0)

    selected_indices = []
    n_entries = wcsim_tree.GetEntries()

    for i_entry in range(n_entries):
        wcsim_tree.GetEntry(i_entry)

        n_triggers = event.GetNumberOfEvents()
        if n_triggers == 1:
            trigger = event.GetTrigger(0)
            n_digi_hits = trigger.GetNcherenkovdigihits()
            if n_digi_hits <= 0:
                print(f"Event {i_entry + 1} rejected: no digitized hits.\n")
                continue
            else:
                find_muon, find_electron = filter_tracks(trigger)
                if not (find_muon and find_electron):
                    print(
                        f"Event {i_entry + 1} rejected: "
                        f"muon found: {find_muon}, electron found: {find_electron}.\n"
                    )
                    continue
                else:
                    output_tree.Fill()
                    selected_indices.append(i_entry)
        else:
            print(f"Event {i_entry + 1} rejected: {n_triggers} triggers.\n")
    output_tree.Write()
    output_root.Close()
    input_root.Close()

    print(f"Selected events: {len(selected_indices)}")
    print(f"Rejected events: {n_entries - len(selected_indices)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter WCSim ROOT file by trigger count."
    )
    parser.add_argument("input_file", help="Path to input WCSim ROOT file.")
    args = parser.parse_args()

    main(args.input_file)
