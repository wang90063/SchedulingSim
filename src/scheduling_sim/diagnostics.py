from collections import Counter
from dataclasses import asdict, dataclass, field

from scheduling_sim.models import UserEquipment


def classify_dominance_label(
    *,
    is_pending: bool,
    in_candidate_window: bool,
    hol_ms: int,
    pdb_ms: int | None,
) -> str:
    if not is_pending:
        return "not_pending"
    if not in_candidate_window:
        return "queue_limited"
    if pdb_ms is None:
        return "spectral_dominated"
    if hol_ms >= pdb_ms:
        return "overdue_pdb_forced"
    if hol_ms >= (pdb_ms / 2):
        return "pdb_dominated"
    return "spectral_dominated"


def _inst_rate_bits_per_prb(ue: UserEquipment) -> float:
    if ue.current_radio_state is not None:
        return float(ue.current_radio_state.bits_per_prb)
    return float(ue.radio_profile.bits_per_prb)


def _spectral_term(ue: UserEquipment) -> float:
    avg_rate = max(float(ue.average_throughput), 1.0)
    return _inst_rate_bits_per_prb(ue) / avg_rate


def _hol_factor(hol_ms: int, pdb_ms: int | None) -> float:
    if pdb_ms is None:
        return 1.0
    return hol_ms / max(1, pdb_ms - hol_ms)


def build_target_row(
    *,
    policy: str,
    time_ms: int,
    phase: str,
    target_ue: UserEquipment,
    ordered_queue: list[object],
    candidates: list[UserEquipment],
    ranked: list[UserEquipment],
    ranking_policy,
) -> "DecisionTraceRow":
    head = target_ue.lc.head_packet
    queue_index = ordered_queue.index(target_ue) if target_ue in ordered_queue else None
    queue_rank = (queue_index + 1) if queue_index is not None else (len(ordered_queue) + 1)
    in_candidate_window = target_ue in candidates
    candidate_rank_epf = (ranked.index(target_ue) + 1) if target_ue in ranked else None
    spectral_sorted = sorted(candidates, key=_spectral_term, reverse=True)
    candidate_rank_spectral_only = (spectral_sorted.index(target_ue) + 1) if target_ue in spectral_sorted else None
    spectral_term = _spectral_term(target_ue)
    hol_factor = _hol_factor(target_ue.hol_ms, None if head is None else head.pdb_ms)
    pdb_slack_ms = (head.pdb_ms - target_ue.hol_ms) if head is not None and head.pdb_ms is not None else None
    if ranking_policy is not None and hasattr(ranking_policy, "weight"):
        epf_weight = float(ranking_policy.weight(target_ue))
    else:
        epf_weight = spectral_term * hol_factor
    dominance_label = classify_dominance_label(
        is_pending=head is not None,
        in_candidate_window=in_candidate_window,
        hol_ms=target_ue.hol_ms,
        pdb_ms=None if head is None else head.pdb_ms,
    )
    return DecisionTraceRow(
        policy=policy,
        time_ms=time_ms,
        phase=phase,
        queue_rank=queue_rank,
        in_candidate_window=in_candidate_window,
        candidate_rank_epf=candidate_rank_epf,
        candidate_rank_spectral_only=candidate_rank_spectral_only,
        inst_rate_bits_per_prb=_inst_rate_bits_per_prb(target_ue),
        average_throughput=target_ue.average_throughput,
        spectral_term=spectral_term,
        hol_ms=target_ue.hol_ms,
        pdb_ms=None if head is None else head.pdb_ms,
        pdb_slack_ms=pdb_slack_ms,
        hol_factor=hol_factor,
        epf_weight=epf_weight,
        dominance_label=dominance_label,
    )


@dataclass(slots=True)
class DecisionTraceRow:
    policy: str
    time_ms: int
    phase: str
    queue_rank: int
    in_candidate_window: bool
    candidate_rank_epf: int | None
    candidate_rank_spectral_only: int | None
    inst_rate_bits_per_prb: float
    average_throughput: float
    spectral_term: float
    hol_ms: int
    pdb_ms: int | None
    pdb_slack_ms: int | None
    hol_factor: float
    epf_weight: float
    dominance_label: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class TargetEdgeDiagnosticCollector:
    policy: str
    rows: list[DecisionTraceRow] = field(default_factory=list)

    def record(self, row: DecisionTraceRow) -> None:
        self.rows.append(row)

    def capture(
        self,
        *,
        queue,
        candidates: list[UserEquipment],
        ranked: list[UserEquipment],
        ranking_policy,
        time_ms: int,
        phase: str,
    ) -> None:
        target_ue = None
        ordered_queue = queue.ordered_users()
        for ue in ordered_queue:
            head = ue.lc.head_packet
            if head is not None and head.is_target:
                target_ue = ue
                break
        if target_ue is None:
            return
        self.record(
            build_target_row(
                policy=self.policy,
                time_ms=time_ms,
                phase=phase,
                target_ue=target_ue,
                ordered_queue=ordered_queue,
                candidates=candidates,
                ranked=ranked,
                ranking_policy=ranking_policy,
            )
        )


def summarize_trace(rows: list[DecisionTraceRow]) -> dict[str, object]:
    counts = Counter(row.dominance_label for row in rows)
    first_candidate_time_ms = next(
        (row.time_ms for row in rows if row.in_candidate_window),
        None,
    )
    first_rank1_time_ms = next(
        (row.time_ms for row in rows if row.candidate_rank_epf == 1),
        None,
    )
    first_pdb_dominated_time_ms = next(
        (
            row.time_ms
            for row in rows
            if row.dominance_label in {"pdb_dominated", "overdue_pdb_forced"}
        ),
        None,
    )
    return {
        "first_candidate_time_ms": first_candidate_time_ms,
        "first_rank1_time_ms": first_rank1_time_ms,
        "first_pdb_dominated_time_ms": first_pdb_dominated_time_ms,
        "queue_limited_count": counts.get("queue_limited", 0),
        "spectral_dominated_count": counts.get("spectral_dominated", 0),
        "pdb_dominated_count": counts.get("pdb_dominated", 0),
        "overdue_pdb_forced_count": counts.get("overdue_pdb_forced", 0),
    }
