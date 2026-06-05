import statistics


class MetricsCollector:
    def __init__(self) -> None:
        self.completed_packets: list[dict[str, object]] = []
        self.served_bits_total = 0
        self.served_bits_by_group = {"center": 0, "edge": 0}
        self.served_bits_by_user: dict[str, int] = {}
        self.used_prb_by_group = {"center": 0, "edge": 0}
        self.radio_stats_by_user: dict[str, dict[str, float | int | str]] = {}

    def record_bits_served(self, user_class: str, bits_sent: int, ue_id: str | None = None) -> None:
        normalized_class = user_class if user_class in self.served_bits_by_group else "center"
        self.served_bits_total += bits_sent
        self.served_bits_by_group[normalized_class] += bits_sent
        if ue_id is not None:
            self.served_bits_by_user[ue_id] = self.served_bits_by_user.get(ue_id, 0) + bits_sent

    def record_prb_used(self, user_class: str, prb_count: int) -> None:
        normalized_class = user_class if user_class in self.used_prb_by_group else "center"
        self.used_prb_by_group[normalized_class] += prb_count

    def record_radio_state(self, user) -> None:
        state = getattr(user, "current_radio_state", None)
        if state is None:
            return
        stats = self.radio_stats_by_user.setdefault(
            user.ue_id,
            {
                "ue_id": user.ue_id,
                "user_class": "edge" if user.is_edge_user else "center",
                "distance_to_bs_m": float(getattr(user.radio_profile, "distance_to_bs_m", 0.0)),
                "initial_sinr_db": float(state.snr_db),
                "initial_mcs_index": int(state.mcs_index),
                "initial_bits_per_prb": int(state.bits_per_prb),
                "sinr_sum_db": 0.0,
                "sinr_count": 0,
                "sinr_min_db": float(state.snr_db),
                "sinr_max_db": float(state.snr_db),
            },
        )
        stats["distance_to_bs_m"] = float(getattr(user.radio_profile, "distance_to_bs_m", 0.0))
        stats["sinr_sum_db"] = float(stats["sinr_sum_db"]) + float(state.snr_db)
        stats["sinr_count"] = int(stats["sinr_count"]) + 1
        stats["sinr_min_db"] = min(float(stats["sinr_min_db"]), float(state.snr_db))
        stats["sinr_max_db"] = max(float(stats["sinr_max_db"]), float(state.snr_db))

    def build_user_radio_rows(self, users) -> list[dict[str, float | int | str]]:
        rows: list[dict[str, float | int | str]] = []
        for user in users:
            stats = self.radio_stats_by_user.get(user.ue_id)
            if stats is None:
                continue
            sinr_count = int(stats["sinr_count"])
            sinr_mean = 0.0 if sinr_count == 0 else float(stats["sinr_sum_db"]) / float(sinr_count)
            rows.append(
                {
                    "ue_id": str(stats["ue_id"]),
                    "user_class": str(stats["user_class"]),
                    "distance_to_bs_m": float(stats["distance_to_bs_m"]),
                    "initial_sinr_db": float(stats["initial_sinr_db"]),
                    "sinr_mean_db": sinr_mean,
                    "sinr_min_db": float(stats["sinr_min_db"]),
                    "sinr_max_db": float(stats["sinr_max_db"]),
                    "initial_mcs_index": int(stats["initial_mcs_index"]),
                    "initial_bits_per_prb": int(stats["initial_bits_per_prb"]),
                }
            )
        return rows

    def record_packet_completed(
        self,
        packet_id: str,
        completion_time: int,
        arrival_time: int,
        pdb_ms: int | None,
        bits_sent: int,
        user_class: str = "center",
        ue_id: str | None = None,
        is_target: bool = False,
        first_service_time: int | None = None,
        service_slot_count: int = 0,
        control_slot_count_while_pending: int = 0,
        waiting_u_slot_count_before_first_service: int = 0,
        waiting_u_slot_count_after_first_service: int = 0,
    ) -> None:
        self.completed_packets.append(
            {
                "packet_id": packet_id,
                "ue_id": ue_id,
                "delay_ms": completion_time - arrival_time,
                "arrival_time": arrival_time,
                "pdb_ms": pdb_ms,
                "bits_sent": bits_sent,
                "user_class": user_class,
                "is_target": is_target,
                "first_service_time": first_service_time,
                "service_slot_count": service_slot_count,
                "control_slot_count_while_pending": control_slot_count_while_pending,
                "waiting_u_slot_count_before_first_service": waiting_u_slot_count_before_first_service,
                "waiting_u_slot_count_after_first_service": waiting_u_slot_count_after_first_service,
            }
        )

    @staticmethod
    def _percentile(values: list[int], ratio: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        return float(sorted_values[int(ratio * (len(sorted_values) - 1))])

    def build_summary(
        self,
        total_prb_used: int,
        total_prb_available: int,
        users=None,
        simulation_duration_ms: int = 0,
        slot_duration_ms: int = 1,
        tdd_pattern: str = "DSUUU",
    ) -> dict[str, float]:
        user_list = list(users or [])
        delays = [item["delay_ms"] for item in self.completed_packets] or [0]
        pdb_packets = [item for item in self.completed_packets if item["pdb_ms"] is not None]
        violations = [item for item in pdb_packets if item["delay_ms"] > item["pdb_ms"]]
        center_packets = [item for item in self.completed_packets if item["user_class"] == "center"]
        edge_packets = [item for item in self.completed_packets if item["user_class"] == "edge"]
        edge_pdb_packets = [item for item in edge_packets if item["pdb_ms"] is not None]
        center_users = [user for user in user_list if not user.is_edge_user]
        edge_users = [user for user in user_list if user.is_edge_user]
        simulation_duration_seconds = simulation_duration_ms / 1000.0 if simulation_duration_ms > 0 else 0.0
        center_total_bits = float(self.served_bits_by_group["center"])
        edge_total_bits = float(self.served_bits_by_group["edge"])
        system_total_bits = float(self.served_bits_total)
        center_used_prb = float(self.used_prb_by_group["center"])
        edge_used_prb = float(self.used_prb_by_group["edge"])
        center_rates_bps = [
            self.served_bits_by_user.get(user.ue_id, 0) / simulation_duration_seconds
            for user in center_users
        ] if simulation_duration_seconds > 0 else []
        center_gbr_users = [
            user for user in center_users if getattr(getattr(user, "traffic_profile", None), "gbr_bps", 0.0) > 0.0
        ]
        center_gbr_satisfied = [
            user
            for user in center_gbr_users
            if simulation_duration_seconds > 0
            and (self.served_bits_by_user.get(user.ue_id, 0) / simulation_duration_seconds)
            >= getattr(user.traffic_profile, "gbr_bps", 0.0)
        ]
        edge_hol_values = [
            int(user.hol_ms)
            for user in edge_users
            if getattr(user.lc, "head_packet", None) is not None
        ]
        edge_overdue_hol_count = sum(
            1
            for user in edge_users
            if getattr(user.lc, "head_packet", None) is not None
            and user.lc.head_packet.pdb_ms is not None
            and user.hol_ms > user.lc.head_packet.pdb_ms
        )
        edge_backlog_bits = sum(
            packet.remaining_bits
            for user in edge_users
            for packet in user.lc.packets
        )
        target_completed = next(
            (item for item in self.completed_packets if item.get("is_target")),
            None,
        )
        target_pending = None
        for user in edge_users:
            for packet in user.lc.packets:
                if packet.is_target:
                    target_pending = {"packet": packet, "ue_id": user.ue_id}
                    break
            if target_pending is not None:
                break
        target_summary = {
            "target_edge_tracked": False,
            "target_edge_finished": False,
            "target_edge_completion_delay_ms": 0.0,
            "target_edge_queue_wait_ms": 0.0,
            "target_edge_service_time_ms": 0.0,
            "target_edge_control_phase_wait_ms": 0.0,
            "target_edge_pre_first_service_wait_ms": 0.0,
            "target_edge_inter_service_gap_wait_ms": 0.0,
            "target_edge_time_to_first_service_ms": 0.0,
            "target_edge_pdb_met": False,
            "target_edge_served_bits": 0.0,
            "target_edge_remaining_bits": 0.0,
        }
        if target_completed is not None:
            service_time_ms = float(int(target_completed.get("service_slot_count", 0)) * slot_duration_ms)
            control_wait_ms = float(int(target_completed.get("control_slot_count_while_pending", 0)) * slot_duration_ms)
            pre_first_wait_ms = float(
                int(target_completed.get("waiting_u_slot_count_before_first_service", 0)) * slot_duration_ms
            )
            inter_service_gap_wait_ms = float(
                int(target_completed.get("waiting_u_slot_count_after_first_service", 0)) * slot_duration_ms
            )
            queue_wait_ms = control_wait_ms + pre_first_wait_ms + inter_service_gap_wait_ms
            completion_delay_ms = queue_wait_ms + service_time_ms
            first_service_time = target_completed.get("first_service_time")
            arrival_time = int(target_completed.get("arrival_time", 0))
            target_summary = {
                "target_edge_tracked": True,
                "target_edge_finished": True,
                "target_edge_completion_delay_ms": completion_delay_ms,
                "target_edge_queue_wait_ms": queue_wait_ms,
                "target_edge_service_time_ms": service_time_ms,
                "target_edge_control_phase_wait_ms": control_wait_ms,
                "target_edge_pre_first_service_wait_ms": pre_first_wait_ms,
                "target_edge_inter_service_gap_wait_ms": inter_service_gap_wait_ms,
                "target_edge_time_to_first_service_ms": (
                    float(first_service_time - arrival_time)
                    if first_service_time is not None
                    else 0.0
                ),
                "target_edge_pdb_met": bool(
                    target_completed["pdb_ms"] is not None
                    and completion_delay_ms <= float(target_completed["pdb_ms"])
                ),
                "target_edge_served_bits": float(target_completed["bits_sent"]),
                "target_edge_remaining_bits": 0.0,
            }
        elif target_pending is not None:
            packet = target_pending["packet"]
            elapsed_ms = max(0, simulation_duration_ms - packet.arrival_time)
            service_time_ms = float(packet.service_slot_count * slot_duration_ms)
            control_wait_ms = float(packet.control_slot_count_while_pending * slot_duration_ms)
            pre_first_wait_ms = float(packet.waiting_u_slot_count_before_first_service * slot_duration_ms)
            inter_service_gap_wait_ms = float(packet.waiting_u_slot_count_after_first_service * slot_duration_ms)
            queue_wait_ms = control_wait_ms + pre_first_wait_ms + inter_service_gap_wait_ms
            time_to_first_service_ms = (
                float(packet.first_service_time - packet.arrival_time)
                if packet.first_service_time is not None
                else float(elapsed_ms)
            )
            target_summary = {
                "target_edge_tracked": True,
                "target_edge_finished": False,
                "target_edge_completion_delay_ms": 0.0,
                "target_edge_queue_wait_ms": queue_wait_ms,
                "target_edge_service_time_ms": service_time_ms,
                "target_edge_control_phase_wait_ms": control_wait_ms,
                "target_edge_pre_first_service_wait_ms": pre_first_wait_ms,
                "target_edge_inter_service_gap_wait_ms": inter_service_gap_wait_ms,
                "target_edge_time_to_first_service_ms": time_to_first_service_ms,
                "target_edge_pdb_met": False,
                "target_edge_served_bits": float(packet.served_bits),
                "target_edge_remaining_bits": float(packet.remaining_bits),
            }
        target_edge_total_bits = float(target_summary["target_edge_served_bits"])
        center_agg_rate_bps = center_total_bits / simulation_duration_seconds if simulation_duration_seconds > 0 else 0.0
        edge_agg_rate_bps = edge_total_bits / simulation_duration_seconds if simulation_duration_seconds > 0 else 0.0
        target_edge_rate_bps = target_edge_total_bits / simulation_duration_seconds if simulation_duration_seconds > 0 else 0.0
        system_agg_rate_bps = system_total_bits / simulation_duration_seconds if simulation_duration_seconds > 0 else 0.0
        return {
            "avg_delay_ms": statistics.mean(delays),
            "p95_delay_ms": self._percentile(delays, 0.95),
            "p99_delay_ms": self._percentile(delays, 0.99),
            "simulation_duration_ms": float(simulation_duration_ms),
            "analysis_window_ms": float(simulation_duration_ms),
            "pdb_violation_rate": len(violations) / len(self.completed_packets) if self.completed_packets else 0.0,
            "throughput_bits": sum(item["bits_sent"] for item in self.completed_packets),
            "served_bits": self.served_bits_total,
            "center_served_bits": self.served_bits_by_group["center"],
            "edge_served_bits": self.served_bits_by_group["edge"],
            "prb_utilization": total_prb_used / total_prb_available if total_prb_available else 0.0,
            "center_total_bits": center_total_bits,
            "edge_total_bits": edge_total_bits,
            "target_edge_total_bits": target_edge_total_bits,
            "system_total_bits": system_total_bits,
            "center_agg_rate_bps": center_agg_rate_bps,
            "edge_agg_rate_bps": edge_agg_rate_bps,
            "target_edge_rate_bps": target_edge_rate_bps,
            "system_agg_rate_bps": system_agg_rate_bps,
            "center_used_prb": center_used_prb,
            "edge_used_prb": edge_used_prb,
            "center_prb_share": (center_used_prb / total_prb_used) if total_prb_used else 0.0,
            "edge_prb_share": (edge_used_prb / total_prb_used) if total_prb_used else 0.0,
            "center_bits_per_used_prb": (center_total_bits / center_used_prb) if center_used_prb > 0 else 0.0,
            "edge_bits_per_used_prb": (edge_total_bits / edge_used_prb) if edge_used_prb > 0 else 0.0,
            "completed_packets": len(self.completed_packets),
            "center_completed_packets": len(center_packets),
            "edge_completed_packets": len(edge_packets),
            "center_avg_delay_ms": statistics.mean([item["delay_ms"] for item in center_packets]) if center_packets else 0.0,
            "edge_avg_delay_ms": statistics.mean([item["delay_ms"] for item in edge_packets]) if edge_packets else 0.0,
            "edge_p95_delay_ms": self._percentile([int(item["delay_ms"]) for item in edge_packets], 0.95),
            "edge_pdb_satisfaction_rate": (
                sum(1 for item in edge_pdb_packets if item["delay_ms"] <= item["pdb_ms"]) / len(edge_pdb_packets)
                if edge_pdb_packets
                else 0.0
            ),
            "center_avg_rate_bps": statistics.mean(center_rates_bps) if center_rates_bps else 0.0,
            "center_min_rate_bps": min(center_rates_bps) if center_rates_bps else 0.0,
            "center_user_gbr_satisfaction_rate": (
                len(center_gbr_satisfied) / len(center_gbr_users)
                if center_gbr_users
                else 1.0
            ),
            "edge_avg_hol_ms": statistics.mean(edge_hol_values) if edge_hol_values else 0.0,
            "edge_p95_hol_ms": self._percentile(edge_hol_values, 0.95),
            "edge_overdue_hol_ratio": (
                edge_overdue_hol_count / len(edge_hol_values)
                if edge_hol_values
                else 0.0
            ),
            "edge_backlog_bits": float(edge_backlog_bits),
            **target_summary,
        }
