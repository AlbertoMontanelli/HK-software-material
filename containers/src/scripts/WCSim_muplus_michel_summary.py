#!/usr/bin/env python3

"""
Create a compact ROOT summary for single-trigger muon + Michel-lepton
WCSim samples.

The input sample is expected to contain exactly one WCSim trigger object
per event.

The output ROOT file contains:

    1. EventSummary
        One flat entry per WCSim event, containing:
        - event-level hit and charge information;
        - true muon information;
        - true Michel electron/positron information;
        - truth composition of the digitized hits.

    2. PmtHitMap
        One entry per WCSim event, with one vector element per digitized PMT.

        Since the inspected sample contains at most one digi-hit object per
        PMT in each trigger, no merging by tube ID is performed.

        Each digi-hit stores:
        - tube ID;
        - digitized charge;
        - digitized time;
        - number of contributing true hits associated with the muon branch;
        - number associated with the Michel-lepton branch;
        - number produced by dark noise;
        - number associated with other particles;
        - estimated charge fractions;
        - a truth label.

    3. Geometry
        One entry containing the PMT geometry.

Truth association chain:

    WCSimRootCherenkovDigiHit
        -> GetPhotonIds()
        -> WCSimRootCherenkovHitTime
        -> GetParentSavedTrackID()
        -> WCSimRootTrack ancestry

The ancestry is followed because a Cherenkov photon may have been produced
by a secondary particle descending from the primary muon or from the
Michel electron/positron.

The Michel branch is checked before the muon branch because the Michel
lepton is itself a descendant of the muon.
"""

import argparse
from array import array
from pathlib import Path

import numpy as np
import ROOT  # type: ignore

# Truth labels stored in PmtHitMap.
LABEL_UNKNOWN = 0
LABEL_MUON_ONLY = 1
LABEL_MICHEL_ONLY = 2
LABEL_MUON_MICHEL_MIXED = 3
LABEL_DARK_ONLY = 4
LABEL_OTHER_ONLY = 5
LABEL_COMPLEX_MIXED = 6


def load_wcsim_library():
    """Load the WCSim ROOT dictionary."""

    status = ROOT.gSystem.Load("libWCSimRoot.so")

    if status < 0:
        raise RuntimeError("Could not load libWCSimRoot.so")


def get_tracks(trigger):
    """
    Return true WCSim tracks as dictionaries.

    GetId() and GetParentId() are used to reconstruct the particle ancestry.
    """

    tracks = []

    n_tracks = int(trigger.GetNtrack())
    true_tracks = trigger.GetTracks()

    for track_index in range(n_tracks):
        track = true_tracks.At(track_index)

        start = np.array(
            [
                float(track.GetStart(0)),
                float(track.GetStart(1)),
                float(track.GetStart(2)),
            ],
            dtype=float,
        )

        stop = np.array(
            [
                float(track.GetStop(0)),
                float(track.GetStop(1)),
                float(track.GetStop(2)),
            ],
            dtype=float,
        )

        direction = np.array(
            [
                float(track.GetDir(0)),
                float(track.GetDir(1)),
                float(track.GetDir(2)),
            ],
            dtype=float,
        )

        direction_norm = np.linalg.norm(direction)

        if direction_norm > 0.0:
            direction = direction / direction_norm

        mass = float(track.GetM())
        energy = float(track.GetE())

        tracks.append(
            {
                "index": int(track_index),
                "id": int(track.GetId()),
                "parent_id": int(track.GetParentId()),
                "ipnu": int(track.GetIpnu()),
                "parent_type": int(track.GetParenttype()),
                "creator": str(track.GetCreatorProcessName()),
                "start": start,
                "stop": stop,
                "direction": direction,
                "M": mass,
                "p": float(track.GetP()),
                "E": energy,
                "K": energy - mass,
                "time": float(track.GetTime()),
            }
        )

    return tracks


def find_primary_muon(tracks, entry_index):
    """
    Find the unique generated primary muon.

    The function accepts both mu+ and mu-:
        PDG(mu-) = 13
        PDG(mu+) = -13
    """

    candidates = [
        track
        for track in tracks
        if (
            abs(int(track["ipnu"])) == 13
            and int(track["parent_type"]) == 0
            and str(track["creator"]) == "initial"
            and float(track["M"]) > 0.0
        )
    ]

    if len(candidates) != 1:
        print(
            f"WARNING: entry {entry_index}: found {len(candidates)} "
            "primary muon candidates, expected 1."
        )
        return None

    return candidates[0]


def find_michel_lepton(tracks, muon_track, entry_index):
    """
    Find the Michel electron or positron directly produced by muon decay.

    For a mu+ sample, the expected Michel lepton is a positron:
        mu+ -> e+ + nu_e + anti-nu_mu

    For a mu- sample, the expected Michel lepton is an electron:
        mu- -> e- + anti-nu_e + nu_mu
    """

    if muon_track is None:
        return None

    muon_id = int(muon_track["id"])

    candidates = [
        track
        for track in tracks
        if (
            abs(int(track["ipnu"])) == 11
            and int(track["parent_id"]) == muon_id
            and str(track["creator"]) == "Decay"
            and float(track["M"]) > 0.0
        )
    ]

    if len(candidates) != 1:
        print(
            f"WARNING: entry {entry_index}: found {len(candidates)} "
            "Michel electron/positron candidates, expected 1."
        )
        return None

    return candidates[0]


def build_parent_map(tracks):
    """
    Build a map:

        track ID -> parent track ID

    The map is used to follow the ancestry of a true PMT hit back to
    the primary muon or Michel lepton.
    """

    return {int(track["id"]): int(track["parent_id"]) for track in tracks}


def descends_from(track_id, ancestor_id, parent_map):
    """
    Return True when track_id is ancestor_id or descends from ancestor_id.

    A protection against malformed ancestry loops is included.
    """

    current_id = int(track_id)
    ancestor_id = int(ancestor_id)

    # Safe-guard against malformed ancestry loops. Set() create a new
    # empty set where duplicate values are ignored.
    visited = set()

    while current_id not in visited:
        if current_id == ancestor_id:
            return True

        visited.add(current_id)

        if current_id not in parent_map:
            return False

        parent_id = int(parent_map[current_id])

        if parent_id < 0 or parent_id == current_id:
            return False

        current_id = parent_id

    return False


def classify_parent_track(
    parent_track_id,
    muon_track_id,
    michel_track_id,
    parent_map,
):
    """
    Classify the saved parent track of one true PMT hit.

    The Michel ancestry must be checked first because the Michel lepton
    itself descends from the muon.
    """

    parent_track_id = int(parent_track_id)

    if parent_track_id == -1:
        return "dark"

    if descends_from(
        track_id=parent_track_id,
        ancestor_id=michel_track_id,
        parent_map=parent_map,
    ):
        return "michel"

    if descends_from(
        track_id=parent_track_id,
        ancestor_id=muon_track_id,
        parent_map=parent_map,
    ):
        return "muon"

    return "other"


def determine_truth_label(
    n_muon,
    n_michel,
    n_dark,
    n_other,
):
    """Assign a truth label to one digitized hit."""

    has_muon = n_muon > 0
    has_michel = n_michel > 0
    has_dark = n_dark > 0
    has_other = n_other > 0

    n_present_components = sum(
        [
            has_muon,
            has_michel,
            has_dark,
            has_other,
        ]
    )

    if n_present_components == 0:
        return LABEL_UNKNOWN

    if has_muon and not has_michel and not has_dark and not has_other:
        return LABEL_MUON_ONLY

    if has_michel and not has_muon and not has_dark and not has_other:
        return LABEL_MICHEL_ONLY

    if has_muon and has_michel and not has_dark and not has_other:
        return LABEL_MUON_MICHEL_MIXED

    if has_dark and not has_muon and not has_michel and not has_other:
        return LABEL_DARK_ONLY

    if has_other and not has_muon and not has_michel and not has_dark:
        return LABEL_OTHER_ONLY

    return LABEL_COMPLEX_MIXED


def analyse_digi_hits(trigger, muon_track, michel_track, tracks):
    """
    Analyse all digitized hits in one trigger.

    Each PMT is expected to appear in at most one digi-hit object.

    Returns
    -------
    result : dict
        Event-level quantities and per-PMT vectors.
    """

    parent_map = build_parent_map(tracks)

    muon_track_id = int(muon_track["id"])
    michel_track_id = int(michel_track["id"])

    true_hit_times = trigger.GetCherenkovHitTimes()
    digi_hits = trigger.GetCherenkovDigiHits()

    n_digi_hits = int(trigger.GetNcherenkovdigihits())

    tube_ids = []
    charges = []
    times = []

    n_muon_true_hits_vector = []
    n_michel_true_hits_vector = []
    n_dark_true_hits_vector = []
    n_other_true_hits_vector = []

    muon_fraction_vector = []
    michel_fraction_vector = []

    estimated_muon_charge_vector = []
    estimated_michel_charge_vector = []

    truth_label_vector = []

    seen_tube_ids = set()

    event_n_muon_true_hits = 0
    event_n_michel_true_hits = 0
    event_n_dark_true_hits = 0
    event_n_other_true_hits = 0

    n_muon_only_digi_hits = 0
    n_michel_only_digi_hits = 0
    n_muon_michel_mixed_digi_hits = 0
    n_dark_only_digi_hits = 0
    n_other_only_digi_hits = 0
    n_complex_mixed_digi_hits = 0
    n_unknown_digi_hits = 0

    total_charge = 0.0
    estimated_muon_charge_total = 0.0
    estimated_michel_charge_total = 0.0

    for digi_hit_index in range(n_digi_hits):
        digi_hit = digi_hits.At(digi_hit_index)

        tube_id = int(digi_hit.GetTubeId())
        charge = float(digi_hit.GetQ())
        time = float(digi_hit.GetT())

        if tube_id in seen_tube_ids:
            raise RuntimeError(
                "Repeated digitized PMT found despite the expected "
                f"one-digit-per-PMT structure: tube_id={tube_id}"
            )

        seen_tube_ids.add(tube_id)

        n_muon = 0
        n_michel = 0
        n_dark = 0
        n_other = 0

        photon_ids = digi_hit.GetPhotonIds()

        for photon_id in photon_ids:
            true_hit = true_hit_times.At(int(photon_id))

            if true_hit is None:
                n_other += 1
                continue

            parent_track_id = int(true_hit.GetParentSavedTrackID())

            component = classify_parent_track(
                parent_track_id=parent_track_id,
                muon_track_id=muon_track_id,
                michel_track_id=michel_track_id,
                parent_map=parent_map,
            )

            if component == "muon":
                n_muon += 1
            elif component == "michel":
                n_michel += 1
            elif component == "dark":
                n_dark += 1
            else:
                n_other += 1

        n_total_contributors = n_muon + n_michel + n_dark + n_other

        if n_total_contributors > 0:
            muon_fraction = n_muon / n_total_contributors
            michel_fraction = n_michel / n_total_contributors
        else:
            muon_fraction = 0.0
            michel_fraction = 0.0

        estimated_muon_charge = charge * muon_fraction
        estimated_michel_charge = charge * michel_fraction

        truth_label = determine_truth_label(
            n_muon=n_muon,
            n_michel=n_michel,
            n_dark=n_dark,
            n_other=n_other,
        )

        if truth_label == LABEL_MUON_ONLY:
            n_muon_only_digi_hits += 1
        elif truth_label == LABEL_MICHEL_ONLY:
            n_michel_only_digi_hits += 1
        elif truth_label == LABEL_MUON_MICHEL_MIXED:
            n_muon_michel_mixed_digi_hits += 1
        elif truth_label == LABEL_DARK_ONLY:
            n_dark_only_digi_hits += 1
        elif truth_label == LABEL_OTHER_ONLY:
            n_other_only_digi_hits += 1
        elif truth_label == LABEL_COMPLEX_MIXED:
            n_complex_mixed_digi_hits += 1
        else:
            n_unknown_digi_hits += 1

        tube_ids.append(tube_id)
        charges.append(charge)
        times.append(time)

        n_muon_true_hits_vector.append(n_muon)
        n_michel_true_hits_vector.append(n_michel)
        n_dark_true_hits_vector.append(n_dark)
        n_other_true_hits_vector.append(n_other)

        muon_fraction_vector.append(muon_fraction)
        michel_fraction_vector.append(michel_fraction)

        estimated_muon_charge_vector.append(estimated_muon_charge)
        estimated_michel_charge_vector.append(estimated_michel_charge)

        truth_label_vector.append(truth_label)

        event_n_muon_true_hits += n_muon
        event_n_michel_true_hits += n_michel
        event_n_dark_true_hits += n_dark
        event_n_other_true_hits += n_other

        total_charge += charge
        estimated_muon_charge_total += estimated_muon_charge
        estimated_michel_charge_total += estimated_michel_charge

    return {
        "n_digi_hits": n_digi_hits,
        "n_unique_digi_tubes": len(seen_tube_ids),
        "tot_charge": total_charge,
        "min_time": min(times) if times else np.nan,
        "max_time": max(times) if times else np.nan,
        "time_span": (max(times) - min(times) if times else np.nan),
        "n_muon_true_hits": event_n_muon_true_hits,
        "n_michel_true_hits": event_n_michel_true_hits,
        "n_dark_true_hits": event_n_dark_true_hits,
        "n_other_true_hits": event_n_other_true_hits,
        "n_muon_only_digi_hits": n_muon_only_digi_hits,
        "n_michel_only_digi_hits": n_michel_only_digi_hits,
        "n_muon_michel_mixed_digi_hits": (n_muon_michel_mixed_digi_hits),
        "n_dark_only_digi_hits": n_dark_only_digi_hits,
        "n_other_only_digi_hits": n_other_only_digi_hits,
        "n_complex_mixed_digi_hits": n_complex_mixed_digi_hits,
        "n_unknown_digi_hits": n_unknown_digi_hits,
        "estimated_muon_charge": estimated_muon_charge_total,
        "estimated_michel_charge": estimated_michel_charge_total,
        "tube_id": tube_ids,
        "charge": charges,
        "time": times,
        "pmt_n_muon_true_hits": n_muon_true_hits_vector,
        "pmt_n_michel_true_hits": n_michel_true_hits_vector,
        "pmt_n_dark_true_hits": n_dark_true_hits_vector,
        "pmt_n_other_true_hits": n_other_true_hits_vector,
        "muon_fraction": muon_fraction_vector,
        "michel_fraction": michel_fraction_vector,
        "estimated_muon_charge_vector": (estimated_muon_charge_vector),
        "estimated_michel_charge_vector": (estimated_michel_charge_vector),
        "truth_label": truth_label_vector,
    }


def fill_geometry_tree(input_root_file, output_root_file):
    """
    Copy PMT geometry into a compact Geometry tree.

    WCSim convention:
        cyl_loc = 0: top cap
        cyl_loc = 1: barrel wall
        cyl_loc = 2: bottom cap
    """

    geo_tree_in = input_root_file.Get("wcsimGeoT")

    if not geo_tree_in:
        raise RuntimeError("Could not find tree 'wcsimGeoT' in input file.")

    geom = ROOT.WCSimRootGeom()

    geo_tree_in.SetBranchAddress(
        "wcsimrootgeom",
        ROOT.AddressOf(geom),
    )

    geo_tree_in.GetEntry(0)

    output_root_file.cd()

    geo_tree = ROOT.TTree(
        "Geometry",
        "Compact PMT geometry",
    )

    tube_id_vector = ROOT.std.vector("int")()
    cyl_loc_vector = ROOT.std.vector("int")()

    x_vector = ROOT.std.vector("float")()
    y_vector = ROOT.std.vector("float")()
    z_vector = ROOT.std.vector("float")()

    geo_tree.Branch("tube_id", tube_id_vector)
    geo_tree.Branch("cyl_loc", cyl_loc_vector)

    geo_tree.Branch("x", x_vector)
    geo_tree.Branch("y", y_vector)
    geo_tree.Branch("z", z_vector)

    n_pmts = int(geom.GetWCNumPMT())

    for pmt_index in range(n_pmts):
        pmt = geom.GetPMT(pmt_index)

        tube_id_vector.push_back(int(pmt.GetTubeNo()))

        cyl_loc_vector.push_back(int(pmt.GetCylLoc()))

        x_vector.push_back(float(pmt.GetPosition(0)))

        y_vector.push_back(float(pmt.GetPosition(1)))

        z_vector.push_back(float(pmt.GetPosition(2)))

    geo_tree.Fill()
    geo_tree.Write()

    print(f"Saved Geometry tree with {n_pmts} PMTs")


def create_output_trees(output_root):
    """
    Create EventSummary and PmtHitMap trees.

    The returned dictionaries contain the buffers that must remain alive
    for the whole duration of the event loop.
    """

    output_root.cd()

    # ============================================================
    # EventSummary
    # ============================================================

    event_tree = ROOT.TTree(
        "EventSummary",
        "Flat per-event muon and Michel summary",
    )

    event_branch = {}

    # Event identification and hit counts
    event_branch["entry_index"] = array("i", [0])
    event_branch["n_triggers"] = array("i", [0])

    event_branch["n_raw_tubes_hit"] = array("i", [0])
    event_branch["n_true_hits"] = array("i", [0])

    event_branch["n_digi_hits"] = array("i", [0])
    event_branch["n_digi_tubes_hit"] = array("i", [0])

    # Event-level digitized quantities
    event_branch["tot_charge"] = array("f", [np.nan])
    event_branch["min_time"] = array("f", [np.nan])
    event_branch["max_time"] = array("f", [np.nan])
    event_branch["time_span"] = array("f", [np.nan])

    # Truth composition of all digi-hits
    event_branch["n_muon_true_hits"] = array("i", [0])
    event_branch["n_michel_true_hits"] = array("i", [0])
    event_branch["n_dark_true_hits"] = array("i", [0])
    event_branch["n_other_true_hits"] = array("i", [0])

    event_branch["n_muon_only_digi_hits"] = array("i", [0])
    event_branch["n_michel_only_digi_hits"] = array("i", [0])
    event_branch["n_muon_michel_mixed_digi_hits"] = array("i", [0])
    event_branch["n_dark_only_digi_hits"] = array("i", [0])
    event_branch["n_other_only_digi_hits"] = array("i", [0])
    event_branch["n_complex_mixed_digi_hits"] = array("i", [0])
    event_branch["n_unknown_digi_hits"] = array("i", [0])

    event_branch["estimated_muon_charge"] = array("f", [0.0])
    event_branch["estimated_michel_charge"] = array("f", [0.0])

    # Decay information
    event_branch["decay_time_ns"] = array("f", [np.nan])

    # True muon information
    event_branch["muon_track_length_cm"] = array("f", [np.nan])

    event_branch["muon_true_id"] = array("i", [0])
    event_branch["muon_true_ipnu"] = array("i", [0])

    event_branch["muon_true_p"] = array("f", [np.nan])
    event_branch["muon_true_E"] = array("f", [np.nan])
    event_branch["muon_true_K"] = array("f", [np.nan])
    event_branch["muon_true_M"] = array("f", [np.nan])
    event_branch["muon_true_time"] = array("f", [np.nan])

    event_branch["muon_true_start"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )
    event_branch["muon_true_stop"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )
    event_branch["muon_true_dir"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )

    # True Michel information
    event_branch["michel_track_length_cm"] = array("f", [np.nan])

    event_branch["michel_true_id"] = array("i", [0])
    event_branch["michel_true_ipnu"] = array("i", [0])

    event_branch["michel_true_p"] = array("f", [np.nan])
    event_branch["michel_true_E"] = array("f", [np.nan])
    event_branch["michel_true_K"] = array("f", [np.nan])
    event_branch["michel_true_M"] = array("f", [np.nan])
    event_branch["michel_true_time"] = array("f", [np.nan])

    event_branch["michel_true_start"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )
    event_branch["michel_true_stop"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )
    event_branch["michel_true_dir"] = array(
        "f",
        [np.nan, np.nan, np.nan],
    )

    # ------------------------------------------------------------
    # Scalar branches
    # ------------------------------------------------------------

    event_tree.Branch(
        "entry_index",
        event_branch["entry_index"],
        "entry_index/I",
    )
    event_tree.Branch(
        "n_triggers",
        event_branch["n_triggers"],
        "n_triggers/I",
    )

    event_tree.Branch(
        "n_raw_tubes_hit",
        event_branch["n_raw_tubes_hit"],
        "n_raw_tubes_hit/I",
    )
    event_tree.Branch(
        "n_true_hits",
        event_branch["n_true_hits"],
        "n_true_hits/I",
    )

    event_tree.Branch(
        "n_digi_hits",
        event_branch["n_digi_hits"],
        "n_digi_hits/I",
    )
    event_tree.Branch(
        "n_digi_tubes_hit",
        event_branch["n_digi_tubes_hit"],
        "n_digi_tubes_hit/I",
    )

    event_tree.Branch(
        "tot_charge",
        event_branch["tot_charge"],
        "tot_charge/F",
    )
    event_tree.Branch(
        "min_time",
        event_branch["min_time"],
        "min_time/F",
    )
    event_tree.Branch(
        "max_time",
        event_branch["max_time"],
        "max_time/F",
    )
    event_tree.Branch(
        "time_span",
        event_branch["time_span"],
        "time_span/F",
    )

    event_tree.Branch(
        "n_muon_true_hits",
        event_branch["n_muon_true_hits"],
        "n_muon_true_hits/I",
    )
    event_tree.Branch(
        "n_michel_true_hits",
        event_branch["n_michel_true_hits"],
        "n_michel_true_hits/I",
    )
    event_tree.Branch(
        "n_dark_true_hits",
        event_branch["n_dark_true_hits"],
        "n_dark_true_hits/I",
    )
    event_tree.Branch(
        "n_other_true_hits",
        event_branch["n_other_true_hits"],
        "n_other_true_hits/I",
    )

    event_tree.Branch(
        "n_muon_only_digi_hits",
        event_branch["n_muon_only_digi_hits"],
        "n_muon_only_digi_hits/I",
    )
    event_tree.Branch(
        "n_michel_only_digi_hits",
        event_branch["n_michel_only_digi_hits"],
        "n_michel_only_digi_hits/I",
    )
    event_tree.Branch(
        "n_muon_michel_mixed_digi_hits",
        event_branch["n_muon_michel_mixed_digi_hits"],
        "n_muon_michel_mixed_digi_hits/I",
    )
    event_tree.Branch(
        "n_dark_only_digi_hits",
        event_branch["n_dark_only_digi_hits"],
        "n_dark_only_digi_hits/I",
    )
    event_tree.Branch(
        "n_other_only_digi_hits",
        event_branch["n_other_only_digi_hits"],
        "n_other_only_digi_hits/I",
    )
    event_tree.Branch(
        "n_complex_mixed_digi_hits",
        event_branch["n_complex_mixed_digi_hits"],
        "n_complex_mixed_digi_hits/I",
    )
    event_tree.Branch(
        "n_unknown_digi_hits",
        event_branch["n_unknown_digi_hits"],
        "n_unknown_digi_hits/I",
    )

    event_tree.Branch(
        "estimated_muon_charge",
        event_branch["estimated_muon_charge"],
        "estimated_muon_charge/F",
    )
    event_tree.Branch(
        "estimated_michel_charge",
        event_branch["estimated_michel_charge"],
        "estimated_michel_charge/F",
    )

    event_tree.Branch(
        "decay_time_ns",
        event_branch["decay_time_ns"],
        "decay_time_ns/F",
    )

    # Muon branches
    event_tree.Branch(
        "muon_track_length_cm",
        event_branch["muon_track_length_cm"],
        "muon_track_length_cm/F",
    )
    event_tree.Branch(
        "muon_true_id",
        event_branch["muon_true_id"],
        "muon_true_id/I",
    )
    event_tree.Branch(
        "muon_true_ipnu",
        event_branch["muon_true_ipnu"],
        "muon_true_ipnu/I",
    )
    event_tree.Branch(
        "muon_true_p",
        event_branch["muon_true_p"],
        "muon_true_p/F",
    )
    event_tree.Branch(
        "muon_true_E",
        event_branch["muon_true_E"],
        "muon_true_E/F",
    )
    event_tree.Branch(
        "muon_true_K",
        event_branch["muon_true_K"],
        "muon_true_K/F",
    )
    event_tree.Branch(
        "muon_true_M",
        event_branch["muon_true_M"],
        "muon_true_M/F",
    )
    event_tree.Branch(
        "muon_true_time",
        event_branch["muon_true_time"],
        "muon_true_time/F",
    )
    event_tree.Branch(
        "muon_true_start",
        event_branch["muon_true_start"],
        "muon_true_start[3]/F",
    )
    event_tree.Branch(
        "muon_true_stop",
        event_branch["muon_true_stop"],
        "muon_true_stop[3]/F",
    )
    event_tree.Branch(
        "muon_true_dir",
        event_branch["muon_true_dir"],
        "muon_true_dir[3]/F",
    )

    # Michel branches
    event_tree.Branch(
        "michel_track_length_cm",
        event_branch["michel_track_length_cm"],
        "michel_track_length_cm/F",
    )
    event_tree.Branch(
        "michel_true_id",
        event_branch["michel_true_id"],
        "michel_true_id/I",
    )
    event_tree.Branch(
        "michel_true_ipnu",
        event_branch["michel_true_ipnu"],
        "michel_true_ipnu/I",
    )
    event_tree.Branch(
        "michel_true_p",
        event_branch["michel_true_p"],
        "michel_true_p/F",
    )
    event_tree.Branch(
        "michel_true_E",
        event_branch["michel_true_E"],
        "michel_true_E/F",
    )
    event_tree.Branch(
        "michel_true_K",
        event_branch["michel_true_K"],
        "michel_true_K/F",
    )
    event_tree.Branch(
        "michel_true_M",
        event_branch["michel_true_M"],
        "michel_true_M/F",
    )
    event_tree.Branch(
        "michel_true_time",
        event_branch["michel_true_time"],
        "michel_true_time/F",
    )
    event_tree.Branch(
        "michel_true_start",
        event_branch["michel_true_start"],
        "michel_true_start[3]/F",
    )
    event_tree.Branch(
        "michel_true_stop",
        event_branch["michel_true_stop"],
        "michel_true_stop[3]/F",
    )
    event_tree.Branch(
        "michel_true_dir",
        event_branch["michel_true_dir"],
        "michel_true_dir[3]/F",
    )

    # ============================================================
    # PmtHitMap
    # ============================================================

    hit_tree = ROOT.TTree(
        "PmtHitMap",
        "Truth-matched digitized PMT hit map",
    )

    hit_branch = {}

    hit_branch["entry_index"] = array("i", [0])

    hit_branch["tube_id"] = ROOT.std.vector("int")()
    hit_branch["charge"] = ROOT.std.vector("float")()
    hit_branch["time"] = ROOT.std.vector("float")()

    hit_branch["n_muon_true_hits"] = ROOT.std.vector("int")()
    hit_branch["n_michel_true_hits"] = ROOT.std.vector("int")()
    hit_branch["n_dark_true_hits"] = ROOT.std.vector("int")()
    hit_branch["n_other_true_hits"] = ROOT.std.vector("int")()

    hit_branch["muon_fraction"] = ROOT.std.vector("float")()
    hit_branch["michel_fraction"] = ROOT.std.vector("float")()

    hit_branch["estimated_muon_charge"] = ROOT.std.vector("float")()
    hit_branch["estimated_michel_charge"] = ROOT.std.vector("float")()

    hit_branch["truth_label"] = ROOT.std.vector("int")()

    hit_tree.Branch(
        "entry_index",
        hit_branch["entry_index"],
        "entry_index/I",
    )

    hit_tree.Branch("tube_id", hit_branch["tube_id"])
    hit_tree.Branch("charge", hit_branch["charge"])
    hit_tree.Branch("time", hit_branch["time"])

    hit_tree.Branch(
        "n_muon_true_hits",
        hit_branch["n_muon_true_hits"],
    )
    hit_tree.Branch(
        "n_michel_true_hits",
        hit_branch["n_michel_true_hits"],
    )
    hit_tree.Branch(
        "n_dark_true_hits",
        hit_branch["n_dark_true_hits"],
    )
    hit_tree.Branch(
        "n_other_true_hits",
        hit_branch["n_other_true_hits"],
    )

    hit_tree.Branch(
        "muon_fraction",
        hit_branch["muon_fraction"],
    )
    hit_tree.Branch(
        "michel_fraction",
        hit_branch["michel_fraction"],
    )

    hit_tree.Branch(
        "estimated_muon_charge",
        hit_branch["estimated_muon_charge"],
    )
    hit_tree.Branch(
        "estimated_michel_charge",
        hit_branch["estimated_michel_charge"],
    )

    hit_tree.Branch(
        "truth_label",
        hit_branch["truth_label"],
    )

    return {
        "event_tree": event_tree,
        "hit_tree": hit_tree,
        "event_branch": event_branch,
        "hit_branch": hit_branch,
    }


def fill_output_trees(
    handles,
    entry_index,
    trigger,
    muon_track,
    michel_track,
    hit_information,
):
    """
    Fill EventSummary and PmtHitMap for one event.
    """

    event_tree = handles["event_tree"]
    hit_tree = handles["hit_tree"]

    event_branch = handles["event_branch"]
    hit_branch = handles["hit_branch"]

    # ============================================================
    # EventSummary
    # ============================================================

    raw_hits = trigger.GetCherenkovHits()
    n_raw_tubes_hit = int(trigger.GetNcherenkovhits())

    n_true_hits = 0

    for raw_hit_index in range(n_raw_tubes_hit):
        raw_hit = raw_hits.At(raw_hit_index)
        n_true_hits += int(raw_hit.GetTotalPe(1))

    event_branch["entry_index"][0] = int(entry_index)
    event_branch["n_triggers"][0] = 1

    event_branch["n_raw_tubes_hit"][0] = n_raw_tubes_hit
    event_branch["n_true_hits"][0] = n_true_hits

    event_branch["n_digi_hits"][0] = int(hit_information["n_digi_hits"])
    event_branch["n_digi_tubes_hit"][0] = int(hit_information["n_unique_digi_tubes"])

    event_branch["tot_charge"][0] = float(hit_information["tot_charge"])
    event_branch["min_time"][0] = float(hit_information["min_time"])
    event_branch["max_time"][0] = float(hit_information["max_time"])
    event_branch["time_span"][0] = float(hit_information["time_span"])

    event_branch["n_muon_true_hits"][0] = int(hit_information["n_muon_true_hits"])
    event_branch["n_michel_true_hits"][0] = int(hit_information["n_michel_true_hits"])
    event_branch["n_dark_true_hits"][0] = int(hit_information["n_dark_true_hits"])
    event_branch["n_other_true_hits"][0] = int(hit_information["n_other_true_hits"])

    event_branch["n_muon_only_digi_hits"][0] = int(
        hit_information["n_muon_only_digi_hits"]
    )
    event_branch["n_michel_only_digi_hits"][0] = int(
        hit_information["n_michel_only_digi_hits"]
    )
    event_branch["n_muon_michel_mixed_digi_hits"][0] = int(
        hit_information["n_muon_michel_mixed_digi_hits"]
    )
    event_branch["n_dark_only_digi_hits"][0] = int(
        hit_information["n_dark_only_digi_hits"]
    )
    event_branch["n_other_only_digi_hits"][0] = int(
        hit_information["n_other_only_digi_hits"]
    )
    event_branch["n_complex_mixed_digi_hits"][0] = int(
        hit_information["n_complex_mixed_digi_hits"]
    )
    event_branch["n_unknown_digi_hits"][0] = int(hit_information["n_unknown_digi_hits"])

    event_branch["estimated_muon_charge"][0] = float(
        hit_information["estimated_muon_charge"]
    )
    event_branch["estimated_michel_charge"][0] = float(
        hit_information["estimated_michel_charge"]
    )

    event_branch["decay_time_ns"][0] = float(michel_track["time"] - muon_track["time"])

    # ------------------------------------------------------------
    # True muon
    # ------------------------------------------------------------

    muon_start = np.asarray(muon_track["start"], dtype=float)
    muon_stop = np.asarray(muon_track["stop"], dtype=float)
    muon_dir = np.asarray(muon_track["direction"], dtype=float)

    event_branch["muon_track_length_cm"][0] = float(
        np.linalg.norm(muon_stop - muon_start)
    )

    event_branch["muon_true_id"][0] = int(muon_track["id"])
    event_branch["muon_true_ipnu"][0] = int(muon_track["ipnu"])

    event_branch["muon_true_p"][0] = float(muon_track["p"])
    event_branch["muon_true_E"][0] = float(muon_track["E"])
    event_branch["muon_true_K"][0] = float(muon_track["K"])
    event_branch["muon_true_M"][0] = float(muon_track["M"])
    event_branch["muon_true_time"][0] = float(muon_track["time"])

    for coordinate_index in range(3):
        event_branch["muon_true_start"][coordinate_index] = float(
            muon_start[coordinate_index]
        )
        event_branch["muon_true_stop"][coordinate_index] = float(
            muon_stop[coordinate_index]
        )
        event_branch["muon_true_dir"][coordinate_index] = float(
            muon_dir[coordinate_index]
        )

    # ------------------------------------------------------------
    # True Michel electron/positron
    # ------------------------------------------------------------

    michel_start = np.asarray(michel_track["start"], dtype=float)
    michel_stop = np.asarray(michel_track["stop"], dtype=float)
    michel_dir = np.asarray(michel_track["direction"], dtype=float)

    event_branch["michel_track_length_cm"][0] = float(
        np.linalg.norm(michel_stop - michel_start)
    )

    event_branch["michel_true_id"][0] = int(michel_track["id"])
    event_branch["michel_true_ipnu"][0] = int(michel_track["ipnu"])

    event_branch["michel_true_p"][0] = float(michel_track["p"])
    event_branch["michel_true_E"][0] = float(michel_track["E"])
    event_branch["michel_true_K"][0] = float(michel_track["K"])
    event_branch["michel_true_M"][0] = float(michel_track["M"])
    event_branch["michel_true_time"][0] = float(michel_track["time"])

    for coordinate_index in range(3):
        event_branch["michel_true_start"][coordinate_index] = float(
            michel_start[coordinate_index]
        )
        event_branch["michel_true_stop"][coordinate_index] = float(
            michel_stop[coordinate_index]
        )
        event_branch["michel_true_dir"][coordinate_index] = float(
            michel_dir[coordinate_index]
        )

    event_tree.Fill()

    # ============================================================
    # PmtHitMap
    # ============================================================

    hit_branch["entry_index"][0] = int(entry_index)

    hit_branch["tube_id"].clear()
    hit_branch["charge"].clear()
    hit_branch["time"].clear()

    hit_branch["n_muon_true_hits"].clear()
    hit_branch["n_michel_true_hits"].clear()
    hit_branch["n_dark_true_hits"].clear()
    hit_branch["n_other_true_hits"].clear()

    hit_branch["muon_fraction"].clear()
    hit_branch["michel_fraction"].clear()

    hit_branch["estimated_muon_charge"].clear()
    hit_branch["estimated_michel_charge"].clear()

    hit_branch["truth_label"].clear()

    n_digi_hits = len(hit_information["tube_id"])

    for hit_index in range(n_digi_hits):
        hit_branch["tube_id"].push_back(int(hit_information["tube_id"][hit_index]))
        hit_branch["charge"].push_back(float(hit_information["charge"][hit_index]))
        hit_branch["time"].push_back(float(hit_information["time"][hit_index]))

        hit_branch["n_muon_true_hits"].push_back(
            int(hit_information["pmt_n_muon_true_hits"][hit_index])
        )
        hit_branch["n_michel_true_hits"].push_back(
            int(hit_information["pmt_n_michel_true_hits"][hit_index])
        )
        hit_branch["n_dark_true_hits"].push_back(
            int(hit_information["pmt_n_dark_true_hits"][hit_index])
        )
        hit_branch["n_other_true_hits"].push_back(
            int(hit_information["pmt_n_other_true_hits"][hit_index])
        )

        hit_branch["muon_fraction"].push_back(
            float(hit_information["muon_fraction"][hit_index])
        )
        hit_branch["michel_fraction"].push_back(
            float(hit_information["michel_fraction"][hit_index])
        )

        hit_branch["estimated_muon_charge"].push_back(
            float(hit_information["estimated_muon_charge_vector"][hit_index])
        )
        hit_branch["estimated_michel_charge"].push_back(
            float(hit_information["estimated_michel_charge_vector"][hit_index])
        )

        hit_branch["truth_label"].push_back(
            int(hit_information["truth_label"][hit_index])
        )

    hit_tree.Fill()


def make_summary_root(input_file, output_file):
    """Create the muon summary ROOT file."""

    load_wcsim_library()

    input_root = ROOT.TFile.Open(str(input_file))

    if not input_root or input_root.IsZombie():
        raise RuntimeError(f"Could not open input file: {input_file}")

    wcsim_tree = input_root.Get("wcsimT")

    if not wcsim_tree:
        raise RuntimeError("Could not find tree 'wcsimT' in input file.")

    output_root = ROOT.TFile(
        str(output_file),
        "RECREATE",
    )

    if not output_root or output_root.IsZombie():
        raise RuntimeError(f"Could not create output file: {output_file}")

    fill_geometry_tree(
        input_root_file=input_root,
        output_root_file=output_root,
    )
    event = ROOT.WCSimRootEvent()

    wcsim_tree.SetBranchAddress(
        "wcsimrootevent",
        ROOT.AddressOf(event),
    )

    n_entries = int(wcsim_tree.GetEntries())

    print(f"Input WCSim entries: {n_entries}")

    n_wrong_trigger_count = 0
    n_missing_muon = 0
    n_missing_michel = 0
    n_written_events = 0

    handles = create_output_trees(output_root)

    for entry_index in range(n_entries):
        wcsim_tree.GetEntry(entry_index)

        n_triggers = int(event.GetNumberOfEvents())

        if n_triggers != 1:
            n_wrong_trigger_count += 1
            print(
                f"WARNING: entry {entry_index} contains {n_triggers}"
                f" trigger objects; expected exactly 1. Skipping."
            )
            event.ReInitialize()
            continue

        trigger = event.GetTrigger(0)

        tracks = get_tracks(trigger)

        muon_track = find_primary_muon(
            tracks,
            entry_index,
        )

        michel_track = find_michel_lepton(
            tracks,
            muon_track,
            entry_index,
        )

        if muon_track is None or michel_track is None:
            n_missing_muon += 1 if muon_track is None else 0
            n_missing_michel += 1 if michel_track is None else 0
            event.ReInitialize()
            continue

        hit_information = analyse_digi_hits(
            trigger,
            muon_track,
            michel_track,
            tracks,
        )

        fill_output_trees(
            handles=handles,
            entry_index=entry_index,
            trigger=trigger,
            muon_track=muon_track,
            michel_track=michel_track,
            hit_information=hit_information,
        )

        event.ReInitialize()
    output_root.cd()

    handles["event_tree"].Write()
    handles["hit_tree"].Write()

    output_root.Close()
    input_root.Close()

    print()
    print(f"Saved summary ROOT file: {output_file}")
    print(f"Input events: {n_entries}")
    print(f"Written events: {n_written_events}")

    if n_wrong_trigger_count > 0:
        print(
            f"Events skipped because the number of triggers was not 1:"
            f" {n_wrong_trigger_count}"
        )

    if n_missing_muon > 0:
        print(
            f"Events skipped because a unique primary muon was not found:"
            f" {n_missing_muon}"
        )

    if n_missing_michel > 0:
        print(
            f"Events skipped because a unique Michel lepton was not found:"
            f" {n_missing_michel}"
        )


def default_output_path(input_file):
    """Return input_summary.root as the default output path."""

    input_path = Path(input_file)

    if input_path.suffix == ".root":
        return input_path.with_name(input_path.stem + "_summary.root")

    return input_path.with_name(input_path.name + "_summary.root")


def parse_arguments():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Create a compact truth-matched ROOT summary from a "
            "single-trigger muon and Michel-lepton WCSim file."
        )
    )

    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
        help="Input WCSim ROOT file.",
    )

    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help=("Output summary ROOT file. Default: input_summary.root."),
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    input_file = Path(args.input_file)

    if args.output_file is None:
        output_file = default_output_path(input_file)
    else:
        output_file = Path(args.output_file)

    make_summary_root(
        input_file=input_file,
        output_file=output_file,
    )


if __name__ == "__main__":
    main()
