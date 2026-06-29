#!/usr/bin/env python3

import argparse

import ROOT  # type: ignore


def print_available_methods(trigger):
    """
    Print useful methods related to hits, digi hits and trigger information.
    This is only for inspection/debug.
    """
    print()
    print("Available trigger methods containing hit/digi/trig:")
    for name in dir(trigger):
        lname = name.lower()
        if "hit" in lname or "digi" in lname or "trig" in lname:
            print(f"  {name}")


def print_trigger_info(trigger, event_idx, trigger_index):
    """
    Print information about a WCSim trigger object.
    """
    n_digi = int(trigger.GetNcherenkovdigihits())
    n_tracks = int(trigger.GetNtrack())

    print(f"\nEvent {event_idx}, Trigger {trigger_index}")
    print(f"GetNtrack() = {n_tracks}")
    print(f"GetNcherenkovhits() = {int(trigger.GetNcherenkovhits())}")
    print(f"GetNcherenkovhittimes() = {int(trigger.GetNcherenkovhittimes())}")
    print(f"GetNumTubesHit() = {int(trigger.GetNumTubesHit())}")
    print(f"GetNcherenkovdigihits() = {n_digi}")
    print(f"GetNumDigiTubesHit() = {int(trigger.GetNumDigiTubesHit())}")
    print(f"GetTriggerType() = {int(trigger.GetTriggerType())}")


def main(input_file, show_methods=False, event_idx=-1):
    ROOT.gSystem.Load("libWCSimRoot.so")

    root_file = ROOT.TFile.Open(str(input_file))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Could not open input file: {input_file}")

    wcsim_tree = root_file.Get("wcsimT")
    if not wcsim_tree:
        raise RuntimeError("Could not find tree 'wcsimT'.")

    event = ROOT.WCSimRootEvent()
    wcsim_tree.SetBranchAddress("wcsimrootevent", ROOT.AddressOf(event))

    n_entries = int(wcsim_tree.GetEntries())
    if event_idx >= 0:
        n_entries = [event_idx]  # Only process the specified event index
    else:
        n_entries = range(n_entries)  # Process all events

    printed_methods = False
    N_MULTIPLE_TRIGGERS = 0
    N_SINGLE_TRIGGERS = 0

    for event_index in n_entries:
        wcsim_tree.GetEntry(event_index)

        n_wcsim_objects = int(event.GetNumberOfEvents())
        has_subevents = bool(event.HasSubEvents())
        if n_wcsim_objects >= 1 and has_subevents:
            print(f"Warning: Event {event_index} has {n_wcsim_objects} triggers")
            N_MULTIPLE_TRIGGERS += 1
        else:
            N_SINGLE_TRIGGERS += 1

        for trigger_index in range(n_wcsim_objects):
            trigger = event.GetTrigger(trigger_index)

            n_digi = int(trigger.GetNcherenkovdigihits())
            n_tracks = int(trigger.GetNtrack())

            if n_digi <= 0 and n_tracks <= 0:
                print_trigger_info(trigger, event_index, trigger_index)
            # Print methods once, only for the first trigger inspected.
            if show_methods and not printed_methods:
                print_available_methods(trigger)
                printed_methods = True

        event.ReInitialize()

    print(f"Events with multiple triggers: {N_MULTIPLE_TRIGGERS}/{len(n_entries)}")
    print(f"Events with single triggers: {N_SINGLE_TRIGGERS}/{len(n_entries)}")
    root_file.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Debug WCSim trigger objects and digitized hits."
    )
    parser.add_argument("input_file", help="Input WCSim ROOT file")
    parser.add_argument(
        "--event_idx", type=int, default=-1, help="Event index to inspect"
    )
    parser.add_argument(
        "--show_methods",
        action="store_true",
        help="Print available trigger methods containing hit/digi/trig.",
    )

    args = parser.parse_args()

    main(
        input_file=args.input_file,
        event_idx=args.event_idx,
        show_methods=args.show_methods,
    )
