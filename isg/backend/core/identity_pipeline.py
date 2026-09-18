"""
ISG Identity Pipeline — Deterministic, calibrated identity matching.
Never auto-matches on ambiguous evidence. Quarantines on conflict.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import hashlib
import unicodedata
import re
from datetime import date


class IdentityDecision(str, Enum):
    ACCEPT = "ACCEPT"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


class MatchConsequence(str, Enum):
    HIGH = "HIGH"       # Financial disbursement, identity-consequential
    MEDIUM = "MEDIUM"   # Status update
    LOW = "LOW"         # Read-only lookup


@dataclass
class IdentityCandidate:
    """A single identity candidate from the identity system."""
    identity_ref: str
    name: str
    dob: str                      # ISO date string YYYY-MM-DD
    verification_status: str      # VERIFIED / UNVERIFIED / DISPUTED
    source_system: str
    source_version: str


@dataclass
class IdentityClaimant:
    """The identity as claimed by the application."""
    name: str
    dob: str
    application_ref: str


@dataclass
class FeatureScore:
    feature: str
    score: float
    match_type: str
    explanation: str


@dataclass
class CandidateEvaluation:
    candidate: IdentityCandidate
    features: list[FeatureScore]
    composite_score: float
    name_match: bool
    dob_match: bool
    conflict_flags: list[str]


@dataclass
class IdentityDecisionRecord:
    decision: IdentityDecision
    matched_ref: Optional[str]
    composite_score: Optional[float]
    threshold_applied: float
    consequence: MatchConsequence
    candidate_set_hash: str
    candidate_recall_status: str
    evaluations: list[CandidateEvaluation]
    explanation: str
    technical_code: str
    quarantine_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "matched_ref": self.matched_ref,
            "composite_score": self.composite_score,
            "threshold_applied": self.threshold_applied,
            "consequence": self.consequence.value,
            "candidate_set_hash": self.candidate_set_hash,
            "candidate_recall_status": self.candidate_recall_status,
            "explanation": self.explanation,
            "technical_code": self.technical_code,
            "quarantine_reason": self.quarantine_reason,
            "evaluations": [
                {
                    "candidate_ref": e.candidate.identity_ref,
                    "composite_score": e.composite_score,
                    "name_match": e.name_match,
                    "dob_match": e.dob_match,
                    "conflict_flags": e.conflict_flags,
                    "features": [
                        {
                            "feature": f.feature,
                            "score": f.score,
                            "match_type": f.match_type,
                            "explanation": f.explanation,
                        }
                        for f in e.features
                    ],
                }
                for e in self.evaluations
            ],
        }


class IdentityPipeline:
    """
    ISG Identity Pipeline.
    Pipeline: NORMALIZE → CANDIDATE GENERATION → RECALL CHECK →
              FEATURE COMPARISON → CALIBRATED SCORE → CONSEQUENCE-SCOPED THRESHOLD → DECISION
    """

    THRESHOLDS = {
        MatchConsequence.HIGH: 0.95,
        MatchConsequence.MEDIUM: 0.85,
        MatchConsequence.LOW: 0.80,
    }

    def _normalize_name(self, name: str) -> str:
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        name = name.lower().strip()
        name = re.sub(r"[^a-z ]", "", name)
        name = re.sub(r"\s+", " ", name)
        return name

    def _normalize_dob(self, dob: str) -> Optional[date]:
        try:
            return date.fromisoformat(dob.strip())
        except (ValueError, AttributeError):
            return None

    def _score_name(self, claimant_name: str, candidate_name: str) -> FeatureScore:
        cn = self._normalize_name(claimant_name)
        dn = self._normalize_name(candidate_name)

        if cn == dn:
            return FeatureScore(
                feature="name_exact",
                score=1.0,
                match_type="EXACT",
                explanation=f"Names match exactly after normalization: '{cn}'",
            )

        # Token set comparison
        cn_tokens = set(cn.split())
        dn_tokens = set(dn.split())
        if cn_tokens == dn_tokens:
            return FeatureScore(
                feature="name_token_set",
                score=0.92,
                match_type="TOKEN_SET_EXACT",
                explanation="All name tokens match (order differs).",
            )

        # Overlap ratio
        overlap = len(cn_tokens & dn_tokens) / max(len(cn_tokens | dn_tokens), 1)
        if overlap >= 0.8:
            return FeatureScore(
                feature="name_partial",
                score=0.75,
                match_type="PARTIAL",
                explanation=f"Partial name match, overlap={overlap:.2f}.",
            )

        return FeatureScore(
            feature="name_no_match",
            score=0.0,
            match_type="NO_MATCH",
            explanation=f"Names do not match: '{cn}' vs '{dn}'.",
        )

    def _score_dob(self, claimant_dob: str, candidate_dob: str) -> FeatureScore:
        cd = self._normalize_dob(claimant_dob)
        dd = self._normalize_dob(candidate_dob)

        if cd is None or dd is None:
            return FeatureScore(
                feature="dob_unparseable",
                score=0.0,
                match_type="ERROR",
                explanation="Date of birth could not be parsed.",
            )

        if cd == dd:
            return FeatureScore(
                feature="dob_exact",
                score=1.0,
                match_type="EXACT",
                explanation=f"Date of birth matches exactly: {cd}.",
            )

        # Detect transposition errors (day/month swap)
        if cd.year == dd.year and cd.month == dd.day and cd.day == dd.month:
            return FeatureScore(
                feature="dob_transposition",
                score=0.4,
                match_type="TRANSPOSITION_SUSPECTED",
                explanation=(
                    f"Day/month transposition suspected: claimant {cd} vs candidate {dd}. "
                    "This is insufficient for high-consequence matching."
                ),
            )

        days_diff = abs((cd - dd).days)
        if days_diff <= 365:
            return FeatureScore(
                feature="dob_year_conflict",
                score=0.1,
                match_type="YEAR_CONFLICT",
                explanation=(
                    f"Date of birth CONFLICT: claimant DOB {cd} vs candidate DOB {dd}. "
                    f"Difference: {days_diff} days. "
                    "This is a hard disqualifying conflict for identity matching."
                ),
            )

        return FeatureScore(
            feature="dob_mismatch",
            score=0.0,
            match_type="NO_MATCH",
            explanation=f"Date of birth does not match: {cd} vs {dd}.",
        )

    def _evaluate_candidate(
        self, claimant: IdentityClaimant, candidate: IdentityCandidate
    ) -> CandidateEvaluation:
        name_score = self._score_name(claimant.name, candidate.name)
        dob_score = self._score_dob(claimant.dob, candidate.dob)

        conflict_flags = []

        # DOB conflict is a hard disqualifier
        if dob_score.match_type in ("YEAR_CONFLICT", "NO_MATCH", "TRANSPOSITION_SUSPECTED"):
            conflict_flags.append(f"DOB_CONFLICT: {dob_score.explanation}")

        if name_score.score == 0.0:
            conflict_flags.append("NAME_NO_MATCH")

        # Composite: name is required, DOB is required for high-consequence
        # If DOB conflicts, composite is capped at 0.3 regardless of name
        if conflict_flags and any("DOB_CONFLICT" in f for f in conflict_flags):
            composite = min(name_score.score * 0.3, 0.3)
        else:
            composite = name_score.score * 0.6 + dob_score.score * 0.4

        return CandidateEvaluation(
            candidate=candidate,
            features=[name_score, dob_score],
            composite_score=round(composite, 4),
            name_match=name_score.score >= 0.8,
            dob_match=dob_score.score >= 0.9,
            conflict_flags=conflict_flags,
        )

    def _compute_candidate_set_hash(self, candidates: list[IdentityCandidate]) -> str:
        refs = sorted([c.identity_ref for c in candidates])
        return hashlib.sha256("|".join(refs).encode()).hexdigest()[:16]

    def evaluate(
        self,
        claimant: IdentityClaimant,
        candidates: list[IdentityCandidate],
        consequence: MatchConsequence = MatchConsequence.HIGH,
    ) -> IdentityDecisionRecord:
        """
        Run the full identity evaluation pipeline.
        Returns a IdentityDecisionRecord with the decision, score, and explanation.
        """
        threshold = self.THRESHOLDS[consequence]

        if not candidates:
            return IdentityDecisionRecord(
                decision=IdentityDecision.QUARANTINE,
                matched_ref=None,
                composite_score=None,
                threshold_applied=threshold,
                consequence=consequence,
                candidate_set_hash="EMPTY",
                candidate_recall_status="NO_CANDIDATES_FOUND",
                evaluations=[],
                explanation="No identity candidates found for the given identity reference.",
                technical_code="IDN-001-NO-CANDIDATES",
                quarantine_reason="No candidates available for identity matching.",
            )

        evaluations = [self._evaluate_candidate(claimant, c) for c in candidates]
        candidate_set_hash = self._compute_candidate_set_hash(candidates)

        # Find best match
        best = max(evaluations, key=lambda e: e.composite_score)

        # Check for conflicts among candidates with same name
        name_matched = [e for e in evaluations if e.name_match]
        dob_conflicts_among_name_matched = [
            e for e in name_matched if e.conflict_flags and any("DOB_CONFLICT" in f for f in e.conflict_flags)
        ]

        # Name-collision ambiguity: multiple candidates match the name but have conflicting
        # DOBs among themselves — even if one is a perfect match, we cannot reliably
        # distinguish which identity record belongs to the applicant.
        if len(name_matched) > 1 and dob_conflicts_among_name_matched:
            conflict_details = "; ".join(
                f"{e.candidate.identity_ref}(DOB:{e.candidate.dob})"
                for e in name_matched
            )
            return IdentityDecisionRecord(
                decision=IdentityDecision.QUARANTINE,
                matched_ref=None,
                composite_score=best.composite_score,
                threshold_applied=threshold,
                consequence=consequence,
                candidate_set_hash=candidate_set_hash,
                candidate_recall_status="NAME_COLLISION_DOB_AMBIGUITY",
                evaluations=evaluations,
                explanation=(
                    f"Identity QUARANTINED. NAME COLLISION detected: multiple candidates "
                    f"share the name '{evaluations[0].candidate.name}' but have conflicting dates of birth. "
                    f"ISG cannot reliably identify which record belongs to the applicant. "
                    f"Records: {conflict_details}. "
                    f"Human resolution or additional evidence required."
                ),
                technical_code="IDN-002-DOB-CONFLICT",
                quarantine_reason=(
                    f"Name collision with DOB ambiguity: {conflict_details}."
                ),
            )

        if dob_conflicts_among_name_matched and best.composite_score < threshold:
            conflict_details = "; ".join(
                f"{e.candidate.identity_ref}: {', '.join(e.conflict_flags)}"
                for e in dob_conflicts_among_name_matched
            )
            return IdentityDecisionRecord(
                decision=IdentityDecision.QUARANTINE,
                matched_ref=None,
                composite_score=best.composite_score,
                threshold_applied=threshold,
                consequence=consequence,
                candidate_set_hash=candidate_set_hash,
                candidate_recall_status="CANDIDATES_FOUND_CONFLICTS",
                evaluations=evaluations,
                explanation=(
                    f"Identity QUARANTINED. Name matches found but DATE OF BIRTH CONFLICTS detected. "
                    f"Best composite score {best.composite_score:.3f} is below the "
                    f"{consequence.value}-consequence threshold of {threshold}. "
                    f"ISG does not auto-match when DOB conflicts with a name match. "
                    f"Conflict details: {conflict_details}."
                ),
                technical_code="IDN-002-DOB-CONFLICT",
                quarantine_reason=(
                    f"Name matches but DOB conflicts detected. "
                    f"Score {best.composite_score:.3f} < threshold {threshold}."
                ),
            )

        if best.composite_score >= threshold:
            return IdentityDecisionRecord(
                decision=IdentityDecision.ACCEPT,
                matched_ref=best.candidate.identity_ref,
                composite_score=best.composite_score,
                threshold_applied=threshold,
                consequence=consequence,
                candidate_set_hash=candidate_set_hash,
                candidate_recall_status="MATCH_FOUND",
                evaluations=evaluations,
                explanation=(
                    f"Identity ACCEPTED. Best candidate '{best.candidate.identity_ref}' "
                    f"with composite score {best.composite_score:.3f} meets the "
                    f"{consequence.value}-consequence threshold of {threshold}."
                ),
                technical_code="IDN-003-ACCEPTED",
            )

        return IdentityDecisionRecord(
            decision=IdentityDecision.QUARANTINE,
            matched_ref=None,
            composite_score=best.composite_score,
            threshold_applied=threshold,
            consequence=consequence,
            candidate_set_hash=candidate_set_hash,
            candidate_recall_status="LOW_CONFIDENCE",
            evaluations=evaluations,
            explanation=(
                f"Identity QUARANTINED. Best composite score {best.composite_score:.3f} "
                f"is below the {consequence.value}-consequence threshold of {threshold}. "
                "Insufficient confidence for this consequence level."
            ),
            technical_code="IDN-004-LOW-CONFIDENCE",
            quarantine_reason=f"Score {best.composite_score:.3f} < threshold {threshold}.",
        )
