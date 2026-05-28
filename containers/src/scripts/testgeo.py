#!/usr/bin/env python3

import argparse

import ROOT  # type: ignore

WCSIMROOT_LIB = "/opt/WCSimRootConda/install/lib/libWCSimRoot.so"


def inspect_geometry(filename: str, max_pmts: int = 20) -> None:
    """Read and print WCSim detector geometry information."""

    # Load WCSimRoot library and open root file
    ROOT.gSystem.Load(WCSIMROOT_LIB)
    root_file = ROOT.TFile.Open(str(filename), "READ")

    # Read the geomtry tree, get the number of entries
    geo_tree = root_file.Get("wcsimGeoT")
    n_entries = geo_tree.GetEntries()
    print(f"Geometry tree entries: {n_entries}")

    # Create a WCSimRootGeom object to hold the geometry information.
    geom = ROOT.WCSimRootGeom()

    # Attach the geometry branch to the WCSimRootGeom object. When
    # GetEntry is called, the geometry information of the branch will
    # be stored and can be accessed through the WCSimRootGeom object.
    branch = geo_tree.GetBranch("wcsimrootgeom")
    branch.SetAddress(ROOT.AddressOf(geom))

    for entry in range(n_entries):
        geo_tree.GetEntry(entry)

        print(f"\n=== Geometry entry {entry} ===")
        print(f"Cylinder radius: {geom.GetWCCylRadius()}")
        print(f"Cylinder length: {geom.GetWCCylLength()}")
        print(f"PMT radius:      {geom.GetWCPMTRadius()}")

        print(
            "Offset x y z:    "
            f"{geom.GetWCOffset(0)} "
            f"{geom.GetWCOffset(1)} "
            f"{geom.GetWCOffset(2)}"
        )

        n_pmts = geom.GetWCNumPMT()
        print(f"Number of PMTs:  {n_pmts}")

        n_to_print = min(n_pmts, max_pmts)
        print(f"\nPrinting first {n_to_print} PMTs:")

        for i in range(n_to_print):
            pmt = geom.GetPMT(i)

            print(f"\nPMT index: {i}")
            print(f"  tube number:   {pmt.GetTubeNo()}")
            print(f"  cylinder loc:  {pmt.GetCylLoc()}")
            print(
                "  position:      "
                f"{pmt.GetPosition(0)} "
                f"{pmt.GetPosition(1)} "
                f"{pmt.GetPosition(2)}"
            )
            print(
                "  orientation:   "
                f"{pmt.GetOrientation(0)} "
                f"{pmt.GetOrientation(1)} "
                f"{pmt.GetOrientation(2)}"
            )

    root_file.Close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        help="Path to the WCSim ROOT file inside the container.",
    )
    parser.add_argument(
        "--max-pmts",
        type=int,
        default=20,
        help="Maximum number of PMTs to print.",
    )

    args = parser.parse_args()
    inspect_geometry(args.input_file, args.max_pmts)


if __name__ == "__main__":
    main()
