import argparse
from array import array

import ROOT  # type: ignore


def add_seed_info(
    input_file: str,
    events_per_block: int,
    first_seed: int,
) -> None:
    """
    Add a seedInfo tree to a merged WCSim ROOT file.

    Each entry of seedInfo describes one contiguous block of events.
    All blocks contain the same number of events.

    The seed starts from first_seed and increases by 1 for each block.
    """

    root_file = ROOT.TFile.Open(input_file, "UPDATE")
    event_tree = root_file.Get("wcsimT")

    total_events = int(event_tree.GetEntries())
    n_blocks = total_events // events_per_block

    # Remove previous versions of the tree, if present.
    root_file.Delete("seedInfo;*")

    seed_tree = ROOT.TTree(
        "seedInfo",
        "Seed information for contiguous event blocks",
    )

    seed = array("i", [0])
    first_entry = array("q", [0])
    n_events = array("q", [0])

    seed_tree.Branch("seed", seed, "seed/I")
    seed_tree.Branch("first_entry", first_entry, "first_entry/L")
    seed_tree.Branch("n_events", n_events, "n_events/L")

    for block_index in range(n_blocks):
        seed[0] = first_seed + block_index
        first_entry[0] = block_index * events_per_block
        n_events[0] = events_per_block

        seed_tree.Fill()

        last_entry = first_entry[0] + events_per_block - 1

        print(
            f"Block {block_index}: "
            f"entries {first_entry[0]}-{last_entry}, "
            f"seed {seed[0]}"
        )

    root_file.cd()
    seed_tree.Write("", ROOT.TObject.kOverwrite)
    root_file.Close()

    print()
    print(f"Total events: {total_events}")
    print(f"Number of blocks: {n_blocks}")
    print(f"Tree 'seedInfo' added to: {input_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Add a seedInfo tree to a merged WCSim ROOT file. "
            "The events are divided into equal-sized blocks and the seed "
            "is incremented by one for each block."
        )
    )

    parser.add_argument(
        "--input_file",
        required=True,
        help="Merged ROOT file to modify.",
    )

    parser.add_argument(
        "--events_per_block",
        required=True,
        type=int,
        help="Number of consecutive events generated with each seed.",
    )

    parser.add_argument(
        "--first_seed",
        required=True,
        type=int,
        help="Seed associated with the first event block.",
    )

    args = parser.parse_args()

    add_seed_info(
        input_file=args.input_file,
        events_per_block=args.events_per_block,
        first_seed=args.first_seed,
    )


if __name__ == "__main__":
    main()
