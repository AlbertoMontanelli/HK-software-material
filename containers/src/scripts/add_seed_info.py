import argparse
from array import array

import ROOT  # type: ignore


def add_seed_info(
    input_file,
    events_per_seed,
    first_seed,
    n_seeds,
    short_seeds,
):
    """
    Add a seedInfo tree to a merged WCSim ROOT file.

    Each seed corresponds to one contiguous block of entries in wcsimT.
    Normally each seed contains events_per_seed saved events.

    Seeds listed in short_seeds are assumed to contain one fewer saved event,
    e.g. 999 instead of 1000.
    """

    root_file = ROOT.TFile.Open(input_file, "UPDATE")
    event_tree = root_file.Get("wcsimT")
    total_events = int(event_tree.GetEntries())

    short_seed_set = set(short_seeds)

    # Expected number of saved events after accounting for trigger failures.
    expected_events = n_seeds * events_per_seed - len(short_seed_set)

    if expected_events != total_events:
        root_file.Close()
        raise RuntimeError(
            "Mismatch between expected and actual number of events:\n"
            f"  expected: {expected_events}\n"
            f"  actual:   {total_events}"
        )

    # Remove previous versions of the tree, if present.
    root_file.Delete("seedInfo;*")

    seed_tree = ROOT.TTree(
        "seedInfo",
        "Seed information for contiguous WCSim event blocks",
    )

    seed = array("i", [0])
    first_entry = array("q", [0])
    n_events = array("q", [0])

    seed_tree.Branch("seed", seed, "seed/I")
    seed_tree.Branch("first_entry", first_entry, "first_entry/L")
    seed_tree.Branch("n_events", n_events, "n_events/L")

    current_entry = 0

    for seed_value in range(first_seed, first_seed + n_seeds):
        seed[0] = seed_value
        first_entry[0] = current_entry

        if seed_value in short_seed_set:
            n_events[0] = events_per_seed - 1
        else:
            n_events[0] = events_per_seed

        seed_tree.Fill()

        last_entry = first_entry[0] + n_events[0] - 1

        print(
            f"Seed {seed[0]}: "
            f"entries {first_entry[0]}-{last_entry}, "
            f"n_events={n_events[0]}"
        )

        current_entry += n_events[0]

    root_file.cd()
    seed_tree.Write("", ROOT.TObject.kOverwrite)
    root_file.Close()

    print()
    print(f"Total events: {total_events}")
    print(f"Number of seeds: {n_seeds}")
    print(f"Tree 'seedInfo' added to: {input_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Add a seedInfo tree to a merged WCSim ROOT file, "
            "accounting for seeds with fewer saved events."
        )
    )

    parser.add_argument(
        "--input_file",
        required=True,
        help="Merged ROOT file to modify.",
    )

    parser.add_argument(
        "--events_per_seed",
        required=True,
        type=int,
        help="Nominal number of generated events per seed.",
    )

    parser.add_argument(
        "--first_seed",
        required=True,
        type=int,
        help="First seed.",
    )

    parser.add_argument(
        "--n_seeds",
        required=True,
        type=int,
        help="Total number of consecutive seeds.",
    )

    parser.add_argument(
        "--short_seeds",
        nargs="*",
        type=int,
        default=[],
        help=("Seeds with one fewer saved event because one event failed the trigger."),
    )

    args = parser.parse_args()

    add_seed_info(
        input_file=args.input_file,
        events_per_seed=args.events_per_seed,
        first_seed=args.first_seed,
        n_seeds=args.n_seeds,
        short_seeds=args.short_seeds,
    )


if __name__ == "__main__":
    main()
