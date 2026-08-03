import argparse

import ROOT  # type: ignore


def keep_only_first_entry(root_file, tree_name):
    """
    Replace a TTree inside the same ROOT file with a new tree
    containing only its first entry.
    """

    input_tree = root_file.Get(tree_name)
    # Read the entry that must be preserved.

    input_tree.GetEntry(0)
    # Create an in-memory clone with the same branch structure.
    output_tree = input_tree.CloneTree(0)

    # Copy the values currently loaded from entry 0.
    output_tree.Fill()

    # Detach the new tree from the file before deleting the old one.
    output_tree.SetDirectory(0)

    # Remove all existing cycles of the original tree.
    root_file.Delete(f"{tree_name};*")

    # Write the replacement tree into the same file.
    root_file.cd()
    output_tree.Write(tree_name, ROOT.TObject.kOverwrite)

    print(f"{tree_name}: replacement completed.")


def clean_wcsim_metadata(input_file):
    """
    Modify a merged WCSim ROOT file in place.

    wcsimT is left unchanged.
    Only entry 0 is preserved in:
        - wcsimGeoT
        - wcsimRootOptionsT
    """

    root_file = ROOT.TFile.Open(input_file, "UPDATE")
    keep_only_first_entry(root_file, "wcsimGeoT")
    keep_only_first_entry(root_file, "wcsimRootOptionsT")

    # Save the updated directory information.
    root_file.Write("", ROOT.TObject.kOverwrite)

    root_file.Close()

    print(f"\nFile modified successfully: {input_file}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Modify a merged WCSim ROOT file in place, preserving "
            "all wcsimT entries but only entry 0 of wcsimGeoT and "
            "wcsimRootOptionsT."
        )
    )

    parser.add_argument(
        "--input_file",
        required=True,
        help="Merged ROOT file to modify directly.",
    )

    args = parser.parse_args()

    clean_wcsim_metadata(args.input_file)


if __name__ == "__main__":
    main()
