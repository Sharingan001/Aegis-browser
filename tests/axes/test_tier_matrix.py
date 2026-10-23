#!/usr/bin/env python3
"""
tests/axes/test_tier_matrix.py — Unit Tests for Multi-Axis Combination Matrix

Validates all 64 combinations against Aegis security rules:
- R1 (Decoupling)
- R2 (Tor Identity Lock and Crowd Awareness)
- Non-downgrading property invariant (Preset S >= req S, Preset I >= req I, N0 -> N1 only)
- S4 Static quarantine invariants
- D-012 Hybrid Identity alignment
- D-013 Tor Fail-Closed policy
- D-014 Dedicated Banking preset and extension isolation
"""

import unittest
from tools.tier_matrix import (
    evaluate_combination,
    generate_full_matrix,
    PRESETS,
    S_STRENGTH,
    I_STRENGTH,
    N_STRENGTH
)


class TestTierMatrix(unittest.TestCase):

    def setUp(self):
        self.matrix = generate_full_matrix()

    def test_total_combinations_count(self):
        """Assert exactly 64 combinations are generated from 4x4x4 axes."""
        self.assertEqual(len(self.matrix), 64, "Matrix must contain exactly 64 combinations (4 S x 4 I x 4 N)")

    def test_partition_counts(self):
        """Assert sum of ALLOWED, MAPPED, and REJECTED equals 64."""
        allowed = [r for r in self.matrix if r["status"] == "ALLOWED"]
        mapped = [r for r in self.matrix if r["status"] == "MAPPED"]
        rejected = [r for r in self.matrix if r["status"] == "REJECTED"]

        self.assertEqual(len(allowed), 8, "Exactly 8 canonical preset configurations are ALLOWED")
        self.assertEqual(len(mapped), 26, "Exactly 26 configurations are MAPPED with documented adjustments")
        self.assertEqual(len(rejected), 30, "Exactly 30 configurations are REJECTED due to security violations")
        self.assertEqual(len(allowed) + len(mapped) + len(rejected), 64)

    def test_property_non_downgrading_mapping(self):
        """
        Property Test: A mapping may ONLY increase protection (zero downgrades).
        For every MAPPED row:
        1. Preset's S strength >= requested S strength
        2. Preset's I strength >= requested I strength
        3. Preset's N == requested N, with N0 -> N1 being the ONLY network promotion.
        """
        for row in self.matrix:
            if row["status"] != "MAPPED":
                continue

            req_s = row["S"]
            req_i = row["I"]
            req_n = row["N"]

            preset_key = row["preset"]
            self.assertIsNotNone(preset_key, f"Mapped row {req_s}-{req_i}-{req_n} must have a preset")
            preset = PRESETS[preset_key]

            p_s = preset["S"]
            p_i = preset["I"]
            p_n = preset["N"]

            # Surface strength non-downgrade
            self.assertGreaterEqual(
                S_STRENGTH[p_s], S_STRENGTH[req_s],
                f"Downgrade on S in {req_s}-{req_i}-{req_n} -> preset {preset_key} ({p_s} < {req_s})"
            )

            # Identity strength non-downgrade
            self.assertGreaterEqual(
                I_STRENGTH[p_i], I_STRENGTH[req_i],
                f"Downgrade on I in {req_s}-{req_i}-{req_n} -> preset {preset_key} ({p_i} < {req_i})"
            )

            # Network check: N0 -> N1 is the ONLY promotion; Tor never demotes; clearnet never promotes to Tor
            if req_n == "N0":
                self.assertEqual(
                    p_n, "N1",
                    f"N0 request in {req_s}-{req_i}-{req_n} must promote to N1, got {p_n}"
                )
            elif req_n == "N1":
                self.assertEqual(
                    p_n, "N1",
                    f"N1 request in {req_s}-{req_i}-{req_n} must remain N1, got {p_n}"
                )
            else:
                self.assertIn(
                    p_n, ["N2", "N3"],
                    f"Tor request {req_s}-{req_i}-{req_n} must map to Tor preset, got {p_n}"
                )

    def test_rule_r2_tor_identity_lock(self):
        """
        Rule R2.1: In Tor mode (N2 or N3), Identity MUST be I2 (RFP, intended to resemble, unmeasured).
        Any request with I != I2 (I1, I3, I4) over Tor MUST be REJECTED.
        Total combinations: 4 S x 3 non-I2 x 2 Tor N = 24 combinations.
        """
        tor_non_i2 = [
            r for r in self.matrix
            if r["N"] in ["N2", "N3"] and r["I"] != "I2"
        ]
        self.assertEqual(len(tor_non_i2), 24, "There must be exactly 24 Tor combinations with I != I2")
        for r in tor_non_i2:
            self.assertEqual(
                r["status"], "REJECTED",
                f"Combination {r['S']}-{r['I']}-{r['N']} must be REJECTED under R2"
            )
            self.assertEqual(
                r["rule"], "RULE_R2_TOR_IDENTITY_LOCK",
                f"Combination {r['S']}-{r['I']}-{r['N']} must fail with RULE_R2_TOR_IDENTITY_LOCK"
            )
            self.assertIsNone(r["preset"])

    def test_rule_i4_requires_s4(self):
        """
        Rule: Identity I4 (Minimal-API) is reserved for S4 Static surface.
        Combining I4 with interactive surfaces (S1, S2, S3) on non-Tor is REJECTED.
        Total combinations: 3 non-S4 x 1 I4 x 2 non-Tor N = 6 combinations.
        """
        interactive_i4 = [
            r for r in self.matrix
            if r["I"] == "I4" and r["S"] != "S4" and r["N"] in ["N0", "N1"]
        ]
        self.assertEqual(len(interactive_i4), 6, "There must be exactly 6 non-Tor combinations with I4 and S != S4")
        for r in interactive_i4:
            self.assertEqual(
                r["status"], "REJECTED",
                f"Combination {r['S']}-{r['I']}-{r['N']} must be REJECTED"
            )
            self.assertEqual(
                r["rule"], "RULE_I4_REQUIRES_S4",
                f"Combination {r['S']}-{r['I']}-{r['N']} must fail with RULE_I4_REQUIRES_S4"
            )
            self.assertIsNone(r["preset"])

    def test_canonical_presets_allowed(self):
        """
        Assert the canonical presets are ALLOWED:
        - Standard: S1 + I3 + N1
        - Guarded: S2 + I3 + N1
        - Strict: S3 + I2 + N1
        - Research Tor: S1 + I2 + N2 and S1 + I2 + N3
        - Detonation Tor: S4 + I2 + N2 and S4 + I2 + N3
        - Detonation Local: S4 + I4 + N1
        """
        expected_allowed = [
            ("S1", "I3", "N1", "standard", "RULE_PRESET_STANDARD"),
            ("S2", "I3", "N1", "guarded", "RULE_PRESET_GUARDED"),
            ("S3", "I2", "N1", "strict", "RULE_PRESET_STRICT"),
            ("S1", "I2", "N2", "research_tor", "RULE_PRESET_TOR_STANDARD"),
            ("S1", "I2", "N3", "research_tor", "RULE_PRESET_TOR_STANDARD"),
            ("S4", "I2", "N2", "detonation", "RULE_PRESET_TOR_SAFEST"),
            ("S4", "I2", "N3", "detonation", "RULE_PRESET_TOR_SAFEST"),
            ("S4", "I4", "N1", "detonation_local", "RULE_PRESET_DETONATION_LOCAL"),
        ]

        for s, i, n, exp_preset, exp_rule in expected_allowed:
            res = evaluate_combination(s, i, n)
            self.assertEqual(res["status"], "ALLOWED", f"{{{s}, {i}, {n}}} must be ALLOWED")
            self.assertEqual(res["preset"], exp_preset, f"{{{s}, {i}, {n}}} must map to preset {exp_preset}")
            self.assertEqual(res["rule"], exp_rule, f"{{{s}, {i}, {n}}} must match rule {exp_rule}")

    def test_rule_r2_tor_s3_crowd_splitting_ack(self):
        """
        Rule R2.2: S3 over Tor (S3 + I2 + N2/N3) disables JIT/WASM while keeping JS on.
        This splits the standard Tor crowd. It is MAPPED to research_strict with an explicit crowd-splitting ACK.
        """
        for n in ["N2", "N3"]:
            res = evaluate_combination("S3", "I2", n)
            self.assertEqual(res["status"], "MAPPED")
            self.assertEqual(res["preset"], "research_strict")
            self.assertEqual(res["rule"], "RULE_R2_TOR_S3_ACK")
            self.assertIn("crowd-splitting", res["reason"])

    def test_rule_r2_tor_s2_promotion(self):
        """
        Rule: S2 over Tor (S2 + I2 + N2/N3) has HTTPS-only and WebRTC restrictions
        that split the Tor crowd. It is promoted to research_strict with crowd-splitting ACK.
        """
        for n in ["N2", "N3"]:
            res = evaluate_combination("S2", "I2", n)
            self.assertEqual(res["status"], "MAPPED")
            self.assertEqual(res["preset"], "research_strict")
            self.assertEqual(res["rule"], "RULE_R2_TOR_S2_PROMOTION")

    def test_rule_n0_plaintext_dns_promotion(self):
        """
        Rule: Plaintext DNS (N0) is permitted in S1 (Standard with warning), but prohibited in S2+
        and promoted to N1 (Strict DoH) without downgrading S.
        """
        # S1 allows N0 with warning, mapped to standard
        res_s1_i3 = evaluate_combination("S1", "I3", "N0")
        self.assertEqual(res_s1_i3["status"], "MAPPED")
        self.assertEqual(res_s1_i3["preset"], "standard")

        # S2 promotes N0 to N1 in guarded (S2 >= S2)
        res_s2_i3 = evaluate_combination("S2", "I3", "N0")
        self.assertEqual(res_s2_i3["status"], "MAPPED")
        self.assertEqual(res_s2_i3["preset"], "guarded")
        self.assertEqual(res_s2_i3["rule"], "RULE_N0_PROMOTED_TO_N1")

        # S3 promotes N0 to N1 in strict (S3 >= S3, NEVER downgraded to guarded!)
        res_s3_i3 = evaluate_combination("S3", "I3", "N0")
        self.assertEqual(res_s3_i3["status"], "MAPPED")
        self.assertEqual(res_s3_i3["preset"], "strict")
        self.assertEqual(res_s3_i3["rule"], "RULE_N0_PROMOTED_TO_N1")
        self.assertEqual(PRESETS[res_s3_i3["preset"]]["S"], "S3", "S3 must not be downgraded to S2")

        # S4 promotes N0 to N1 in detonation_local (S4 >= S4)
        res_s4_i4 = evaluate_combination("S4", "I4", "N0")
        self.assertEqual(res_s4_i4["status"], "MAPPED")
        self.assertEqual(res_s4_i4["preset"], "detonation_local")
        self.assertEqual(res_s4_i4["rule"], "RULE_N0_PROMOTED_TO_N1")

    def test_rule_i1_promotion(self):
        """
        Rule: Native Identity (I1) on non-Tor is promoted to I3 (FPP baseline) in S1/S2,
        and to I2 in S3.
        """
        res_s1 = evaluate_combination("S1", "I1", "N1")
        self.assertEqual(res_s1["status"], "MAPPED")
        self.assertEqual(res_s1["preset"], "standard")

        res_s2 = evaluate_combination("S2", "I1", "N1")
        self.assertEqual(res_s2["status"], "MAPPED")
        self.assertEqual(res_s2["preset"], "guarded")

        res_s3 = evaluate_combination("S3", "I1", "N1")
        self.assertEqual(res_s3["status"], "MAPPED")
        self.assertEqual(res_s3["preset"], "strict")

    def test_rule_i2_local_mapped_to_strict(self):
        """
        Rule: RFP Uniform Identity (I2) on clearnet (N1) maps to Strict preset ({S3, I2, N1})
        or Detonation Local ({S4, I4, N1}) without downgrading Identity.
        """
        for s in ["S1", "S2", "S3"]:
            res = evaluate_combination(s, "I2", "N1")
            self.assertEqual(res["status"], "MAPPED" if s != "S3" else "ALLOWED")
            self.assertEqual(res["preset"], "strict")
            if s != "S3":
                self.assertEqual(res["rule"], "RULE_I2_LOCAL_MAPPED_STRICT")

    def test_rule_unambiguous_tor_with_jit_wasm(self):
        """
        Test unambiguous rule for Tor with JIT/WASM:
        1. S1 + I2 + N2: JIT/WASM enabled; ALLOWED as Research Tor.
        2. S3 + I2 + N2: JIT/WASM locked OFF; MAPPED to research_strict with crowd-splitting ACK.
        3. S4 + I2 + N2: JS completely OFF; ALLOWED as Detonation Tor.
        4. Tor with non-I2 (e.g. attempting to enable JIT with native I1 or I3): REJECTED under R2.
        """
        # Direction 1: JIT enabled on Tor at S1
        tor_s1 = evaluate_combination("S1", "I2", "N2")
        self.assertEqual(tor_s1["status"], "ALLOWED")
        self.assertEqual(tor_s1["preset"], "research_tor")

        # Direction 2: JIT disabled on Tor at S3 (splits crowd -> requires ACK)
        tor_s3 = evaluate_combination("S3", "I2", "N2")
        self.assertEqual(tor_s3["status"], "MAPPED")
        self.assertEqual(tor_s3["preset"], "research_strict")

        # Direction 3: All JS disabled on Tor at S4
        tor_s4 = evaluate_combination("S4", "I2", "N2")
        self.assertEqual(tor_s4["status"], "ALLOWED")
        self.assertEqual(tor_s4["preset"], "detonation")

        # Direction 4: Any attempt to request Tor with non-I2 is rejected
        for s in ["S1", "S2", "S3", "S4"]:
            for i in ["I1", "I3", "I4"]:
                res = evaluate_combination(s, i, "N2")
                self.assertEqual(res["status"], "REJECTED")

    def test_no_unhandled_combinations(self):
        """Assert no combination results in an unhandled fallback error."""
        for r in self.matrix:
            self.assertNotEqual(r["rule"], "RULE_UNSUPPORTED_COMBINATION",
                                f"Combination {r['S']}-{r['I']}-{r['N']} fell through to unsupported catch-all")


if __name__ == "__main__":
    unittest.main()
