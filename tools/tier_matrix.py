#!/usr/bin/env python3
"""
tools/tier_matrix.py — Aegis 4x4x4 Multi-Axis Combination & Mapping Engine

Evaluates all 64 combinations of Surface (S1..S4), Identity (I1..I4), and Network (N0..N3)
according to Aegis security rules (R1, R2, D-008, D-011, D-012, D-013, D-014, A-001, A-002, A-003).

Classification invariants:
- ALLOWED: Exact match for a canonical preset
- MAPPED: Promoted/adjusted to a preset without downgrade (preset S >= requested S, preset I >= requested I, N0 -> N1 only)
- REJECTED: Prohibited combination with clear security rationale
"""

from typing import Dict, Any, List

# Strength Orderings (strictly non-downgrading property invariant)
# S: S1 (Standard) < S2 (Guarded) < S3 (Strict) < S4 (Static)
# I: I1 (Native) < I3 (FPP Site-keyed) < I2 (RFP Uniform Spoofing) < I4 (Minimal-API)
# N: N0 (Direct) < N1 (Strict DoH) < N2 (Tor) < N3 (Tor + Bridges)
S_STRENGTH = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
I_STRENGTH = {"I1": 1, "I3": 2, "I2": 3, "I4": 4}
N_STRENGTH = {"N0": 0, "N1": 1, "N2": 2, "N3": 3}

# Canonical Presets
PRESETS = {
    "standard": {
        "name": "Standard",
        "S": "S1",
        "I": "I3",
        "N": "N1",
        "desc": "Daily browsing (JIT on, FPP site-keyed noise, Strict DoH)"
    },
    "guarded": {
        "name": "Guarded",
        "S": "S2",
        "I": "I3",
        "N": "N1",
        "desc": "Hardened daily browsing (HTTPS-only, autoplay block, FPP site-keyed noise, Strict DoH)"
    },
    "banking": {
        "name": "Banking",
        "S": "S2",
        "I": "I3",
        "N": "N1",
        "desc": "Dedicated instance for anchored accounts (S2 HTTPS-only, I3 FPP site-keyed noise, Strict DoH, extensions off)"
    },
    "strict": {
        "name": "Strict",
        "S": "S3",
        "I": "I2",
        "N": "N1",
        "desc": "Hardened clearnet browsing (S3 JIT/WASM/WebGL off, I2 RFP intended to resemble unmeasured, Strict DoH)"
    },
    "research_tor": {
        "name": "Research Tor",
        "S": "S1",
        "I": "I2",
        "N": "N2",
        "desc": "Tor browsing (S1 surface, I2 RFP intended to resemble unmeasured, Tor SOCKS5)"
    },
    "research_strict": {
        "name": "Research Strict",
        "S": "S3",
        "I": "I2",
        "N": "N2",
        "desc": "Hardened Tor with crowd-splitting ACK (S3 JIT-off, I2 RFP intended to resemble unmeasured, Tor SOCKS5)"
    },
    "detonation": {
        "name": "Detonation Tor",
        "S": "S4",
        "I": "I2",
        "N": "N2",
        "desc": "Static quarantine over Tor (S4 JS disabled, I2 RFP intended to resemble unmeasured, Tor SOCKS5, ephemeral RAM)"
    },
    "detonation_local": {
        "name": "Detonation Local",
        "S": "S4",
        "I": "I4",
        "N": "N1",
        "desc": "Offline/Local static quarantine (S4 JS disabled, I4 minimal-API, Strict DoH, ephemeral RAM)"
    },
}


def evaluate_combination(s: str, i: str, n: str) -> Dict[str, Any]:
    """
    Evaluate a single (S, I, N) combination.
    Returns dict:
      - status: 'ALLOWED' | 'MAPPED' | 'REJECTED'
      - preset: canonical preset name or None
      - rule: rule ID that determined the outcome
      - reason: human-readable rationale
    """
    assert s in ["S1", "S2", "S3", "S4"], f"Invalid S: {s}"
    assert i in ["I1", "I2", "I3", "I4"], f"Invalid I: {i}"
    assert n in ["N0", "N1", "N2", "N3"], f"Invalid N: {n}"

    is_tor = n in ["N2", "N3"]

    # ──────────────────────────────────────────────────────────────────────────
    # 1. HARD REJECTION RULES
    # ──────────────────────────────────────────────────────────────────────────

    # Rule R2.1: In Tor mode (N2/N3), Identity MUST be I2 (RFP, intended to resemble, unmeasured).
    # I1 (native leaks host parameters), I3 (site-keyed noise creates unique outlier),
    # and I4 (minimal API strips APIs creating unique outlier) are strictly rejected.
    if is_tor and i != "I2":
        return {
            "status": "REJECTED",
            "preset": None,
            "rule": "RULE_R2_TOR_IDENTITY_LOCK",
            "reason": f"R2 violation: Tor mode ({n}) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity {i} splits the crowd or leaks host parameters."
        }

    # Rule R_I4_REQUIRES_S4: Detonation requires S4 (static surface).
    # Identity I4 (minimal API) strips DOM APIs and is dedicated to S4 Static surface.
    # Requesting I4 with interactive JS (S1/S2/S3) is rejected.
    if i == "I4" and s != "S4":
        return {
            "status": "REJECTED",
            "preset": None,
            "rule": "RULE_I4_REQUIRES_S4",
            "reason": f"Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface {s}."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. CANONICAL ALLOWED PRESETS (Exact Matches)
    # ──────────────────────────────────────────────────────────────────────────

    # Standard Preset: S1 + I3 + N1
    if s == "S1" and i == "I3" and n == "N1":
        return {
            "status": "ALLOWED",
            "preset": "standard",
            "rule": "RULE_PRESET_STANDARD",
            "reason": "Exact match for Standard preset (S1 Surface, I3 FPP Site-keyed noise, N1 Strict DoH)."
        }

    # Guarded Preset: S2 + I3 + N1
    if s == "S2" and i == "I3" and n == "N1":
        return {
            "status": "ALLOWED",
            "preset": "guarded",
            "rule": "RULE_PRESET_GUARDED",
            "reason": "Exact match for Guarded preset (S2 Guarded Surface, I3 FPP Site-keyed noise, N1 Strict DoH)."
        }

    # Strict Preset: S3 + I2 + N1
    if s == "S3" and i == "I2" and n == "N1":
        return {
            "status": "ALLOWED",
            "preset": "strict",
            "rule": "RULE_PRESET_STRICT",
            "reason": "Exact match for Strict preset (S3 Strict Surface, I2 RFP intended to resemble unmeasured, N1 Strict DoH)."
        }

    # Standard Tor: S1 + I2 + N2/N3
    if s == "S1" and i == "I2" and is_tor:
        return {
            "status": "ALLOWED",
            "preset": "research_tor",
            "rule": "RULE_PRESET_TOR_STANDARD",
            "reason": f"Exact match for Research Tor preset ({s} Surface, I2 RFP intended to resemble unmeasured, {n} Tor routing)."
        }

    # Static Tor (Detonation): S4 + I2 + N2/N3
    if s == "S4" and i == "I2" and is_tor:
        return {
            "status": "ALLOWED",
            "preset": "detonation",
            "rule": "RULE_PRESET_TOR_SAFEST",
            "reason": f"Exact match for Detonation Tor preset (S4 Static Surface, I2 RFP intended to resemble unmeasured, {n} Tor routing)."
        }

    # Local Detonation: S4 + I4 + N1
    if s == "S4" and i == "I4" and n == "N1":
        return {
            "status": "ALLOWED",
            "preset": "detonation_local",
            "rule": "RULE_PRESET_DETONATION_LOCAL",
            "reason": "Exact match for Detonation Local preset (S4 Static Surface, I4 Minimal-API, N1 Strict DoH, ephemeral RAM)."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # 3. CONDITIONAL / MAPPED COMBINATIONS (Non-Downgrading Invariant Enforced)
    # ──────────────────────────────────────────────────────────────────────────

    # S3 on Tor (Strict Tor): S3 + I2 + N2/N3
    # Allowed ONLY with explicit crowd-splitting ACK.
    if s == "S3" and i == "I2" and is_tor:
        return {
            "status": "MAPPED",
            "preset": "research_strict",
            "rule": "RULE_R2_TOR_S3_ACK",
            "reason": f"Rule R2: S3 (JIT/WASM disabled) over Tor ({n}) splits the standard Tor crowd. Allowed ONLY with explicit user crowd-splitting acknowledgment; maps to Research Strict."
        }

    # S2 on Tor: S2 + I2 + N2/N3
    # S2 features (HTTPS-only, autoplay block) split the Tor crowd.
    # Promoted to S3 Research Strict with explicit crowd-splitting acknowledgment.
    if s == "S2" and i == "I2" and is_tor:
        return {
            "status": "MAPPED",
            "preset": "research_strict",
            "rule": "RULE_R2_TOR_S2_PROMOTION",
            "reason": f"Rule R2: S2 controls over Tor ({n}) split the crowd. Promoted to S3 Research Strict with explicit crowd-splitting acknowledgment."
        }

    # Plaintext DNS (N0) handling:
    # N0 is permitted in S1 (mapped to Standard with warning); in S2+ plaintext DNS is dangerous and promoted to N1 Strict DoH.
    if n == "N0":
        if s == "S1" and i in ["I1", "I3"]:
            return {
                "status": "MAPPED",
                "preset": "standard",
                "rule": "RULE_N0_DIRECT_STANDARD",
                "reason": "Direct DNS (N0) permitted in Standard preset with warning; promoted to N1 Strict DoH in standard preset."
            }
        elif s == "S1" and i == "I2":
            return {
                "status": "MAPPED",
                "preset": "strict",
                "rule": "RULE_N0_PROMOTED_TO_N1",
                "reason": "RFP Identity (I2) on N0 promoted to N1 Strict DoH in Strict preset (no downgrade on I or S)."
            }
        elif s == "S2":
            if i in ["I1", "I3"]:
                return {
                    "status": "MAPPED",
                    "preset": "guarded",
                    "rule": "RULE_N0_PROMOTED_TO_N1",
                    "reason": "Plaintext DNS (N0) prohibited in hardened surface S2. Promoted to N1 Strict DoH in Guarded preset."
                }
            elif i == "I2":
                return {
                    "status": "MAPPED",
                    "preset": "strict",
                    "rule": "RULE_N0_PROMOTED_TO_N1",
                    "reason": "Plaintext DNS (N0) prohibited in hardened surface S2. Promoted to N1 Strict DoH in Strict preset (preserving I2)."
                }
        elif s == "S3":
            return {
                "status": "MAPPED",
                "preset": "strict",
                "rule": "RULE_N0_PROMOTED_TO_N1",
                "reason": "Plaintext DNS (N0) prohibited in hardened surface S3. Promoted to N1 Strict DoH in Strict preset (S3 >= S3, no downgrade)."
            }
        elif s == "S4":
            return {
                "status": "MAPPED",
                "preset": "detonation_local",
                "rule": "RULE_N0_PROMOTED_TO_N1",
                "reason": "Plaintext DNS (N0) prohibited in static surface S4. Promoted to N1 Strict DoH in Detonation Local preset."
            }

    # Native Identity (I1) on Non-Tor (N1):
    # Promoted upward to baseline FPP (I3) or RFP (I2) to avoid raw native fingerprint leakage.
    if i == "I1" and not is_tor:
        if s == "S1":
            return {
                "status": "MAPPED",
                "preset": "standard",
                "rule": "RULE_I1_S1_STANDARD",
                "reason": "Native identity (I1) in S1 maps to Standard preset (promoted to I3 FPP baseline defense)."
            }
        elif s == "S2":
            return {
                "status": "MAPPED",
                "preset": "guarded",
                "rule": "RULE_I1_PROMOTED_GUARDED",
                "reason": "Guarded surface (S2) mandates tracking/fingerprint baseline; I1 promoted to I3 in Guarded preset."
            }
        elif s == "S3":
            return {
                "status": "MAPPED",
                "preset": "strict",
                "rule": "RULE_S3_LOCAL_STRICT",
                "reason": "S3 surface requires hardened instance; I1 promoted to I2 in Strict preset (S3 >= S3, no downgrade)."
            }
        elif s == "S4":
            return {
                "status": "MAPPED",
                "preset": "detonation_local",
                "rule": "RULE_S4_I1_PROMOTED_DETONATION",
                "reason": "Static surface S4 requires minimal identity; I1 promoted to I4 in Detonation Local preset."
            }

    # Identity I2 (RFP, intended to resemble, unmeasured) on Non-Tor (N1):
    # To satisfy non-downgrade invariant (I_preset >= I_requested), I2 requests on clearnet
    # MUST NOT be downgraded to I3. They map to the Strict preset ({S3, I2, N1}) or Detonation Local ({S4, I4, N1}).
    if i == "I2" and not is_tor:
        if s == "S4":
            return {
                "status": "MAPPED",
                "preset": "detonation_local",
                "rule": "RULE_I2_S4_LOCAL_DETONATION",
                "reason": "I2 on local S4 maps to Detonation Local preset (promoted to I4 minimal-API)."
            }
        else:
            return {
                "status": "MAPPED",
                "preset": "strict",
                "rule": "RULE_I2_LOCAL_MAPPED_STRICT",
                "reason": f"RFP Uniform Identity (I2) requested with surface {s}; mapped to Strict preset ({{S3, I2, N1}}) without downgrading Identity."
            }

    # Identity I3 (FPP site-keyed noise) on Non-Tor (N1):
    if i == "I3" and not is_tor:
        if s == "S3":
            return {
                "status": "MAPPED",
                "preset": "strict",
                "rule": "RULE_S3_I3_MAPPED_STRICT",
                "reason": "S3 requested on clearnet DoH maps to Strict preset ({S3, I2, N1}) with identity promoted to I2 RFP (no downgrade on S)."
            }
        elif s == "S4":
            return {
                "status": "MAPPED",
                "preset": "detonation_local",
                "rule": "RULE_S4_I3_MAPPED_DETONATION",
                "reason": "S4 Static surface requires minimal identity; I3 promoted to I4 in Detonation Local preset."
            }

    # Catch-all fallback
    return {
        "status": "REJECTED",
        "preset": None,
        "rule": "RULE_UNSUPPORTED_COMBINATION",
        "reason": f"Unsupported combination {{{s}, {i}, {n}}}. Does not satisfy security cumulativity or instance mapping rules."
    }


def generate_full_matrix() -> List[Dict[str, Any]]:
    """Generate evaluations for all 64 combinations."""
    matrix = []
    for s in ["S1", "S2", "S3", "S4"]:
        for i in ["I1", "I2", "I3", "I4"]:
            for n in ["N0", "N1", "N2", "N3"]:
                res = evaluate_combination(s, i, n)
                matrix.append({
                    "S": s,
                    "I": i,
                    "N": n,
                    **res
                })
    return matrix


def generate_markdown_table(matrix: List[Dict[str, Any]]) -> str:
    """Format the 64-row matrix as clean Markdown."""
    lines = [
        "| # | Requested `{S, I, N}` | Status | Mapped Preset | Governing Rule | Security Rationale |",
        "|---|---|---|---|---|---|"
    ]
    for idx, row in enumerate(matrix, 1):
        status_badge = f"**{row['status']}**"
        preset_str = f"`{row['preset']}`" if row['preset'] else "—"
        rule_str = f"`{row['rule']}`"
        lines.append(f"| {idx:02d} | `{{{row['S']}, {row['I']}, {row['N']}}}` | {status_badge} | {preset_str} | {rule_str} | {row['reason']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    mat = generate_full_matrix()
    allowed_count = sum(1 for r in mat if r["status"] == "ALLOWED")
    mapped_count = sum(1 for r in mat if r["status"] == "MAPPED")
    rejected_count = sum(1 for r in mat if r["status"] == "REJECTED")
    print(f"Total combinations evaluated: {len(mat)}")
    print(f"  ALLOWED:  {allowed_count}")
    print(f"  MAPPED:   {mapped_count}")
    print(f"  REJECTED: {rejected_count}")
