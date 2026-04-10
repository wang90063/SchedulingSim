import statistics


class MetricsCollector:
    def __init__(self) -> None:
        self.completed_packets: list[dict[str, int]] = []

    def record_packet_completed(
        self,
        packet_id: str,
        completion_time: int,
        arrival_time: int,
        pdb_ms: int,
        bits_sent: int,
    ) -> None:
        self.completed_packets.append(
            {
                "packet_id": packet_id,
                "delay_ms": completion_time - arrival_time,
                "pdb_ms": pdb_ms,
                "bits_sent": bits_sent,
            }
        )

    def build_summary(self, total_prb_used: int, total_prb_available: int) -> dict[str, float]:
        delays = [item["delay_ms"] for item in self.completed_packets] or [0]
        violations = [item for item in self.completed_packets if item["delay_ms"] > item["pdb_ms"]]
        return {
            "avg_delay_ms": statistics.mean(delays),
            "p95_delay_ms": sorted(delays)[int(0.95 * (len(delays) - 1))],
            "pdb_violation_rate": len(violations) / len(self.completed_packets) if self.completed_packets else 0.0,
            "throughput_bits": sum(item["bits_sent"] for item in self.completed_packets),
            "prb_utilization": total_prb_used / total_prb_available if total_prb_available else 0.0,
        }
