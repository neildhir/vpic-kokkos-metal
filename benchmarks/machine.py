"""Hardware fingerprint and run conditions of this Mac, for benchmark records.

"Apple M4" alone does not pin down the hardware: each chip ships in several
binned CPU/GPU core counts, the chassis decides sustained thermals, and every
macOS release brings a new Metal compiler, so all of these are recorded. Only
stock macOS tools and the Foundation framework (through ctypes) are used.
Serial numbers and hardware UUIDs are deliberately not recorded.
Adapted from firm3d_metal/benchmarks/machine.py.
"""

import ctypes
import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any

THERMAL_STATES = ("nominal", "fair", "serious", "critical")  # NSProcessInfo order
LIBOBJC = "/usr/lib/libobjc.A.dylib"
FOUNDATION = "/System/Library/Frameworks/Foundation.framework/Foundation"


def _run(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _sysctl(name: str) -> str:
    return _run("sysctl", "-n", name).strip()


def machine() -> dict[str, Any]:
    """Hardware and OS of this Mac.

    Returns
    -------
    dict[str, Any]
        Model name and identifier, chip, CPU core counts (total, performance,
        efficiency), GPU core count, memory [GiB], and macOS version and build.
    """
    prof = json.loads(_run("system_profiler", "-json", "SPHardwareDataType", "SPDisplaysDataType"))
    hw = prof["SPHardwareDataType"][0]
    gpu = next((g for g in prof["SPDisplaysDataType"] if "sppci_cores" in g), {})
    return {
        "model_name": hw.get("machine_name", "unknown"),
        "model_identifier": _sysctl("hw.model"),
        "chip": hw.get("chip_type", "unknown"),
        "cpu_cores": int(_sysctl("hw.physicalcpu")),
        "cpu_performance_cores": int(_sysctl("hw.perflevel0.physicalcpu")),
        "cpu_efficiency_cores": int(_sysctl("hw.perflevel1.physicalcpu")),
        "gpu_cores": int(gpu.get("sppci_cores", 0)),
        "memory_gib": int(_sysctl("hw.memsize")) // 2**30,
        "macos": _run("sw_vers", "-productVersion").strip(),
        "macos_build": _run("sw_vers", "-buildVersion").strip(),
    }


def label(m: dict[str, Any]) -> str:
    """Human-readable hardware label, e.g. for a summary header.

    Examples
    --------
    "MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2"
    """
    return (
        f"{m['model_name']} ({m['model_identifier']}) · {m['chip']} · "
        f"CPU {m['cpu_cores']} ({m['cpu_performance_cores']}P+{m['cpu_efficiency_cores']}E) · "
        f"GPU {m['gpu_cores']}-core · {m['memory_gib']} GiB · macOS {m['macos']}"
    )


def _process_info(selector: bytes, restype: Any) -> Any:
    """Send a no-argument message to [NSProcessInfo processInfo]."""
    objc = ctypes.cdll.LoadLibrary(LIBOBJC)
    ctypes.cdll.LoadLibrary(FOUNDATION)  # registers NSProcessInfo
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    def send(obj: int, sel: bytes, res: Any) -> Any:
        proto = ctypes.CFUNCTYPE(res, ctypes.c_void_p, ctypes.c_void_p)
        return ctypes.cast(objc.objc_msgSend, proto)(obj, objc.sel_registerName(sel))

    info = send(objc.objc_getClass(b"NSProcessInfo"), b"processInfo", ctypes.c_void_p)
    return send(info, selector, restype)


@dataclass(frozen=True)
class BusyProcess:
    """Another process using a lot of CPU."""

    pid: int
    cpu_percent: float
    command: str  # command line, truncated


def busy_processes(threshold_percent: float, exclude: set[int]) -> list[BusyProcess]:
    """Processes above a CPU threshold, by ps's decaying %CPU average.

    Parameters
    ----------
    threshold_percent : float
        %CPU above which a process counts as busy (100 = one full core).
    exclude : set[int]
        PIDs to ignore (this harness and its parents).

    Returns
    -------
    list[BusyProcess]
        Busy processes, busiest first.
    """
    out = _run("ps", "-A", "-o", "pcpu=,pid=,command=")
    found = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        cpu, pid = float(parts[0]), int(parts[1])
        if cpu > threshold_percent and pid not in exclude:
            found.append(BusyProcess(pid, cpu, parts[2][:160]))
    return sorted(found, key=lambda p: -p.cpu_percent)


def own_pids() -> set[int]:
    """This process and its ancestors (the shell, terminal or agent that started it)."""
    pids = set()
    pid = os.getpid()
    while pid > 1 and pid not in pids:
        pids.add(pid)
        out = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True, check=False).stdout
        pid = int(out.strip() or 0)
    return pids


def conditions(threshold_percent: float, exclude: set[int]) -> dict[str, Any]:
    """Run conditions that move wall times: power, thermals, competing load.

    Parameters
    ----------
    threshold_percent : float
        %CPU above which another process is reported as busy.
    exclude : set[int]
        PIDs not to report.

    Returns
    -------
    dict[str, Any]
        ``power_source``, ``low_power_mode``, macOS's coarse ``thermal_state``
        (one of THERMAL_STATES), the 1/5/15-minute ``load_average``, and
        ``busy_processes`` above the threshold.
    """
    batt = _run("pmset", "-g", "batt")
    power = re.search(r"'([^']+)'", batt)
    return {
        "power_source": power.group(1) if power else "unknown",
        "low_power_mode": bool(_process_info(b"isLowPowerModeEnabled", ctypes.c_bool)),
        "thermal_state": THERMAL_STATES[_process_info(b"thermalState", ctypes.c_long)],
        "load_average": [round(x, 2) for x in os.getloadavg()],
        "busy_processes": [p.__dict__ for p in busy_processes(threshold_percent, exclude)],
    }
