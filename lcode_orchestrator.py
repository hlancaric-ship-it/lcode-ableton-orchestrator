"""
L-Code Device Scanner / Orchestrator -- talks to a running Ableton Live 12
session over OSC via AbletonOSC (must be enabled as a Control Surface in
Live's Preferences > Link/Tempo/MIDI first).

Dry-run first: audit_project() only READS from Live, never writes. Nothing
sends a parameter change until execute_command() is called explicitly with
a resolved registry entry.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from pythonosc import udp_client, osc_server, dispatcher


@dataclass
class ParamInfo:
    index: int
    name: str
    value: float
    min: float
    max: float


@dataclass
class DeviceInfo:
    index: int
    name: str
    class_name: str
    params: dict = field(default_factory=dict)  # param_name -> ParamInfo


@dataclass
class TrackInfo:
    index: int
    name: str
    devices: dict = field(default_factory=dict)  # device_name -> DeviceInfo


class LCodeOrchestratorError(Exception):
    pass


class LCodeOrchestrator:
    def __init__(self, ip: str = "127.0.0.1", send_port: int = 11000, receive_port: int = 11001,
                 timeout: float = 2.0):
        self.client = udp_client.SimpleUDPClient(ip, send_port)
        self.timeout = timeout
        self.registry: dict[str, TrackInfo] = {}

        self._dispatcher = dispatcher.Dispatcher()
        self._dispatcher.set_default_handler(self._on_message)
        self._server = osc_server.ThreadingOSCUDPServer((ip, receive_port), self._dispatcher)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

        self._lock = threading.Lock()
        self._pending: dict[str, list] = {}

    def _on_message(self, address, *args):
        with self._lock:
            self._pending.setdefault(address, []).append(args)

    def _query(self, address: str, params: list, response_address: Optional[str] = None,
               timeout: Optional[float] = None):
        """Send an OSC message and block until a reply on response_address arrives
        (defaults to the same address, which is how AbletonOSC's get/ endpoints work)."""
        response_address = response_address or address
        timeout = timeout if timeout is not None else self.timeout
        with self._lock:
            self._pending.pop(response_address, None)
        self.client.send_message(address, params)

        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                results = self._pending.get(response_address)
            if results:
                return results[-1]
            time.sleep(0.02)
        raise LCodeOrchestratorError(f"Timed out waiting for reply to {address}{params}")

    def audit_project(self, verbose: bool = True) -> dict:
        """
        Read-only scan of every track in the current Live set: track name,
        every device on it, and every parameter each device exposes (name +
        current value + range). Populates self.registry, keyed by track name
        then device name then parameter name -- nothing is written to Live.
        """
        self.registry = {}
        num_tracks = self._query("/live/song/get/num_tracks", [])[0]
        track_names = self._query("/live/song/get/track_names", [])

        for t_idx in range(num_tracks):
            t_name = track_names[t_idx]
            track = TrackInfo(index=t_idx, name=t_name)
            if verbose:
                print(f"[{t_idx}] Track: {t_name}")

            try:
                num_devices = self._query("/live/track/get/num_devices", [t_idx])[1]
            except LCodeOrchestratorError:
                num_devices = 0

            for d_idx in range(num_devices):
                d_name = self._query("/live/device/get/name", [t_idx, d_idx])[2]
                d_class = self._query("/live/device/get/class_name", [t_idx, d_idx])[2]
                device = DeviceInfo(index=d_idx, name=d_name, class_name=d_class)

                num_params = self._query("/live/device/get/num_parameters", [t_idx, d_idx])[2]
                if num_params > 0:
                    p_names = self._query("/live/device/get/parameters/name", [t_idx, d_idx])[2:]
                    p_values = self._query("/live/device/get/parameters/value", [t_idx, d_idx])[2:]
                    p_mins = self._query("/live/device/get/parameters/min", [t_idx, d_idx])[2:]
                    p_maxs = self._query("/live/device/get/parameters/max", [t_idx, d_idx])[2:]
                    for p_idx in range(num_params):
                        p_name = p_names[p_idx]
                        device.params[p_name] = ParamInfo(
                            index=p_idx, name=p_name,
                            value=p_values[p_idx], min=p_mins[p_idx], max=p_maxs[p_idx],
                        )

                track.devices[d_name] = device
                if verbose:
                    param_list = ", ".join(device.params.keys()) or "(no exposed parameters)"
                    print(f"    Device: {d_name} ({d_class}) -- params: {param_list}")

            self.registry[t_name] = track

        return self.registry

    def execute_command(self, track_name: str, device_name: str, param_name: str, value: float):
        """
        Look up (track, device, parameter) in the registry built by
        audit_project() and send the value over OSC. Raises
        LCodeOrchestratorError with a clear message if anything can't be
        resolved, rather than silently sending a wrong index.
        """
        track = self.registry.get(track_name)
        if track is None:
            raise LCodeOrchestratorError(
                f"Unknown track {track_name!r}. Known tracks: {list(self.registry.keys())}")

        device = track.devices.get(device_name)
        if device is None:
            raise LCodeOrchestratorError(
                f"Unknown device {device_name!r} on track {track_name!r}. "
                f"Known devices: {list(track.devices.keys())}")

        param = device.params.get(param_name)
        if param is None:
            raise LCodeOrchestratorError(
                f"Unknown parameter {param_name!r} on {track_name}/{device_name}. "
                f"Known parameters: {list(device.params.keys())}")

        if not (param.min <= value <= param.max):
            raise LCodeOrchestratorError(
                f"Value {value} out of range for {param_name} "
                f"(expected {param.min}..{param.max})")

        self.client.send_message(
            "/live/device/set/parameter/value",
            [track.index, device.index, param.index, value],
        )
        param.value = value

    def close(self):
        self._server.shutdown()


if __name__ == "__main__":
    orch = LCodeOrchestrator()
    orch.audit_project()
    orch.close()
