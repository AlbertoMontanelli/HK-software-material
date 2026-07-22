#!/usr/bin/env python3

import argparse
from pathlib import Path

import ROOT  # type: ignore


def load_wcsim_library():
    """Load the WCSim ROOT classes."""
    status = ROOT.gSystem.Load("libWCSimRoot.so")

    if status < 0:
        raise RuntimeError("Could not load libWCSimRoot.so")


def inspect_trigger(trigger, entry_index, verbose=False):
    """
    Inspect one WCSim trigger.

    The function checks:

    1. Whether a PMT receives more than one true photon hit.
    2. Whether the same PMT appears in more than one digi-hit object.
    """

    # ============================================================
    # True photon hits
    # ============================================================

    raw_hits = trigger.GetCherenkovHits()
    n_raw_tubes = int(trigger.GetNcherenkovhits())

    true_hit_multiplicity_by_tube = {}

    for raw_hit_index in range(n_raw_tubes):
        raw_hit = raw_hits.At(raw_hit_index)

        tube_id = int(raw_hit.GetTubeID())
        n_true_hits = int(raw_hit.GetTotalPe(1))

        true_hit_multiplicity_by_tube[tube_id] = n_true_hits

    raw_tubes_with_multiple_true_hits = {
        tube_id: multiplicity
        for tube_id, multiplicity in true_hit_multiplicity_by_tube.items()
        if multiplicity > 1
    }

    # ============================================================
    # Digitized hits
    # ============================================================

    digi_hits = trigger.GetCherenkovDigiHits()
    n_digi_hits = int(trigger.GetNcherenkovdigihits())

    digi_indices_by_tube = {}

    for digi_hit_index in range(n_digi_hits):
        digi_hit = digi_hits.At(digi_hit_index)
        tube_id = int(digi_hit.GetTubeId())

        digi_indices_by_tube.setdefault(tube_id, []).append(digi_hit_index)

    repeated_digi_tubes = {
        tube_id: digi_indices
        for tube_id, digi_indices in digi_indices_by_tube.items()
        if len(digi_indices) > 1
    }

    if repeated_digi_tubes:
        print(
            f"Entry {entry_index}: "
            f"{len(repeated_digi_tubes)} PMTs appear in multiple "
            "digi-hit objects."
        )

    if verbose and repeated_digi_tubes:
        for tube_id, digi_indices in sorted(repeated_digi_tubes.items()):
            print(f"  Tube {tube_id}: {len(digi_indices)} digi-hit objects")

            for digi_hit_index in digi_indices:
                digi_hit = digi_hits.At(digi_hit_index)

                photon_ids = digi_hit.GetPhotonIds()

                print(
                    f"    digi index = {digi_hit_index}, "
                    f"time = {float(digi_hit.GetT()):.3f} ns, "
                    f"charge = {float(digi_hit.GetQ()):.3f}, "
                    f"contributing true hits = {len(photon_ids)}"
                )

    digi_multiplicities = [len(indices) for indices in digi_indices_by_tube.values()]

    return {
        "n_raw_tubes": n_raw_tubes,
        "n_raw_tubes_with_multiple_true_hits": (len(raw_tubes_with_multiple_true_hits)),
        "max_true_hits_on_one_tube": max(
            true_hit_multiplicity_by_tube.values(),
            default=0,
        ),
        "n_digi_hits": n_digi_hits,
        "n_unique_digi_tubes": len(digi_indices_by_tube),
        "n_repeated_digi_tubes": len(repeated_digi_tubes),
        "max_digi_hits_on_one_tube": max(
            digi_multiplicities,
            default=0,
        ),
    }


def main(input_file, max_events=None, verbose=False):
    load_wcsim_library()

    root_file = ROOT.TFile.Open(str(input_file))

    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open input ROOT file: {input_file}")

    wcsim_tree = root_file.Get("wcsimT")

    if not wcsim_tree:
        raise RuntimeError("Could not find the tree 'wcsimT' in the input file.")

    event = ROOT.WCSimRootEvent()

    wcsim_tree.SetBranchAddress(
        "wcsimrootevent",
        ROOT.AddressOf(event),
    )

    n_entries_in_file = int(wcsim_tree.GetEntries())

    if max_events is None:
        n_entries = n_entries_in_file
    else:
        n_entries = min(n_entries_in_file, max_events)

    events_with_wrong_trigger_count = 0

    events_with_multiple_true_hits = 0
    maximum_true_hits_on_one_tube = 0

    events_with_repeated_digi_tubes = 0
    total_repeated_digi_tubes = 0
    maximum_digi_hits_on_one_tube = 0

    print(f"Input file: {input_file}")
    print(f"Entries in file: {n_entries_in_file}")
    print(f"Entries to inspect: {n_entries}")
    print()

    for entry_index in range(n_entries):
        wcsim_tree.GetEntry(entry_index)

        n_triggers = int(event.GetNumberOfEvents())

        if n_triggers != 1:
            events_with_wrong_trigger_count += 1

            print(
                f"WARNING: entry {entry_index} contains "
                f"{n_triggers} trigger objects instead of 1."
            )

            event.ReInitialize()
            continue

        trigger = event.GetTrigger(0)

        result = inspect_trigger(
            trigger=trigger,
            entry_index=entry_index,
            verbose=verbose,
        )

        if result["n_raw_tubes_with_multiple_true_hits"] > 0:
            events_with_multiple_true_hits += 1

        maximum_true_hits_on_one_tube = max(
            maximum_true_hits_on_one_tube,
            result["max_true_hits_on_one_tube"],
        )

        if result["n_repeated_digi_tubes"] > 0:
            events_with_repeated_digi_tubes += 1

            total_repeated_digi_tubes += result["n_repeated_digi_tubes"]

        maximum_digi_hits_on_one_tube = max(
            maximum_digi_hits_on_one_tube,
            result["max_digi_hits_on_one_tube"],
        )

        event.ReInitialize()

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"Events inspected: {n_entries}")
    print(
        "Events skipped because the number of triggers was not 1: "
        f"{events_with_wrong_trigger_count}"
    )

    print()
    print("True photon-hit level:")

    print(
        "  Events with at least one PMT receiving multiple "
        f"true hits: {events_with_multiple_true_hits}"
    )

    print(
        "  Maximum number of true hits received by one PMT: "
        f"{maximum_true_hits_on_one_tube}"
    )

    print()
    print("Digitized-hit level:")

    print(
        "  Events with at least one PMT represented by multiple "
        f"digi-hit objects: {events_with_repeated_digi_tubes}"
    )

    print(
        "  Total repeated PMTs across all inspected events: "
        f"{total_repeated_digi_tubes}"
    )

    print(
        "  Maximum number of digi-hit objects associated with "
        f"one PMT: {maximum_digi_hits_on_one_tube}"
    )

    if events_with_repeated_digi_tubes == 0:
        print()
        print(
            "No PMT appeared in more than one digi-hit object within the same trigger."
        )

    root_file.Close()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Check whether the same PMT receives multiple true "
            "photon hits or appears in multiple digitized hit objects."
        )
    )

    parser.add_argument(
        "--input_file",
        type=Path,
        required=True,
        help="Input WCSim ROOT file.",
    )

    parser.add_argument(
        "--max_events",
        type=int,
        default=None,
        help=("Maximum number of events to inspect. By default, inspect all events."),
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "Print time, charge and number of contributing true "
            "hits for PMTs that appear in multiple digi-hit objects."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    main(
        input_file=args.input_file,
        max_events=args.max_events,
        verbose=args.verbose,
    )
