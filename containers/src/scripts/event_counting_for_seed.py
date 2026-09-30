import ROOT  # type: ignore


def main(filename, seed):
    root_file = ROOT.TFile.Open(str(filename), "READ")
    tree = root_file.Get("wcsimT")
    if tree.GetEntries() != 1000:
        print(f"Filename: {filename}")
        print(f"Seed: {seed}")
        print(f"Number of entries in tree: {tree.GetEntries()}\n")

    root_file.Close()


if __name__ == "__main__":
    for i in range(1, 50):
        filename = f"/WCSim_data/muplus_michel_gps_Tau500ns_seed{i}.root"
        main(filename, i)
