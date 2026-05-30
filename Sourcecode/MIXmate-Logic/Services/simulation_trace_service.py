import threading
import time


class SimulationTraceService:
    def __init__(self):
        # Trace wird aus UI- und Worker-Threads beschrieben.
        self._lock = threading.Lock()
        self._entries = []
        self._next_id = 1

    def log_i2c(self, addr: int, payload: list[int], note: str = ""):
        # Adresse fuer den Monitor lesbar als Hex formatieren.
        addr_hex = f"0x{int(addr) & 0xFF:02X}"
        msg = f"I2C -> {addr_hex} payload={payload}"
        if note:
            # Notiz beschreibt den fachlichen Schritt zum Payload.
            msg = f"{msg} | {note}"
        self.log_text(msg)

    def log_text(self, message: str):
        with self._lock:
            # Fortlaufende ID erleichtert inkrementelles Nachladen im Dialog.
            item = {
                "id": self._next_id,
                "ts": time.strftime("%H:%M:%S"),
                "message": str(message),
            }
            self._entries.append(item)
            self._next_id += 1

    def get_entries_since(self, last_id: int = 0) -> list[dict]:
        with self._lock:
            # Kopien verhindern Aenderungen am internen Trace-Speicher.
            return [dict(x) for x in self._entries if int(x["id"]) > int(last_id)]

    def clear(self):
        with self._lock:
            # Monitor-Reset beginnt wieder bei ID 1.
            self._entries.clear()
            self._next_id = 1


_SIM_TRACE_SINGLETON = SimulationTraceService()


def get_simulation_trace_service() -> SimulationTraceService:
    # Ein gemeinsamer Trace reicht fuer alle Simulationscontroller.
    return _SIM_TRACE_SINGLETON
