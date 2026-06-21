#!/usr/bin/env python3

import argparse

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


def copy_tree(input_file, output_file, tree_name: str) -> None:
    tree = input_file.Get(tree_name)
    output_file.cd()
    tree.CloneTree(-1, "fast").Write()


def main(input_file, output_file):
    load_wcsim_library()
    input_root = ROOT.TFile.Open(str(input_file), "READ")

    wcsim_tree = input_root.Get("wcsimT")

    output_root = ROOT.TFile.Open(str(output_file), "RECREATE")

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
        print(f"Processing entry {i_entry + 1}/{n_entries}")
        wcsim_tree.GetEntry(i_entry)

        n_triggers = event.GetNumberOfEvents()

        if n_triggers == 1:
            output_tree.Fill()
            selected_indices.append(i_entry)
            print(f"Event selected: {n_triggers} trigger.\n")
        else:
            print(f"Event rejected: {n_triggers} triggers.\n")
    output_tree.Write()
    output_root.Close()
    input_root.Close()

    print("Done.")
    print(f"Selected events:   {len(selected_indices)}")
    print(f"Rejected events:   {n_entries - len(selected_indices)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter WCSim ROOT file by trigger count."
    )
    parser.add_argument("input_file", help="Path to input WCSim ROOT file.")
    parser.add_argument("output_file", help="Path to output WCSim ROOT file.")
    args = parser.parse_args()

    main(args.input_file, args.output_file)
