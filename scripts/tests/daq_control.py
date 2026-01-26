import sys
import time
import json
import shutil
import logging
import datetime
import numpy as np
from time import sleep
from pathlib import Path
from enum import Enum, auto
from impisc.et_daqbox.daq_box_api import DaqBoxConfig, DaqBoxInterface, START, STOP, WAVEFORM_HEADER, parse_spectrum_packet, parse_waveform_packet

class Mode(Enum):
    BOOT = auto()
    IDLE = auto()
    SCIENCE = auto()
    SAFE = auto()

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "impish_logs"
CONFIG_DIR = SCRIPT_DIR / "config"
DEFAULT_CFG = CONFIG_DIR / "default.json"
ACTIVE_CFG = CONFIG_DIR / "active.json"

if not ACTIVE_CFG.exists():
    shutil.copy(DEFAULT_CFG, ACTIVE_CFG)


print("Logging into:", LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR/"daq.log"
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

counters = {
    "waveform": 0,
    "spectrum": 0,
    "stale_ack": 0,
    "unknown": 0,
}
data_counts = [
    ("waveform", 3000),
    ("spectrum", 320),
]

current_mode = Mode.BOOT
acquiring = False

def safe_stop(dbi):
    try:
        dbi.send(STOP)
    except Exception:
        pass
    try:
        dbi.flush()
    except Exception:
        pass

def enter_idle(dbi):
    global current_mode
    safe_stop(dbi)
    current_mode = Mode.IDLE
    logging.info("Entered IDLE mode")

def enter_safe(dbi):
    safe_stop(dbi)
    current_mode = Mode.SAFE

def load_active_config():
    with open(ACTIVE_CFG) as f:
        return json.load(f)

def startup_mode(dbi):
    cfg = load_active_config()
    mode = cfg.get('startup_mode', 'idle')

    if mode == 'idle':
        safe_stop(dbi)
        logging.info('Startup mode: IDLE')
    elif mode == 'science':
        science_mode(dbi)
    else:
        logging.info(f"Unknown startup mode: {mode}, defaulting to IDLE")
        safe_stop(dbi)

def apply_daq_mode(dbi, daq_mode: str):
    """
    Apply global + daq specific config modes
    """
    cfg_dict = load_active_config()

    if daq_mode not in cfg_dict['modes']:
        raise RuntimeError(f'Unknown DAQ mode: {daq_mode}')

    merged = cfg_dict['global'].copy()
    merged.update(cfg_dict['modes'][daq_mode])
    safe_stop(dbi)

    cfg = DaqBoxConfig()

    for key, val in merged.items():
        if key not in DaqBoxConfig._SAVE_ATTRS:
            raise ValueError(f"DaqBoxConfig has no attribute '{key}'")
        setattr(cfg, key, val)

    dbi.send(cfg.to_packet())
    dbi.flush()

    logging.info(
        "DAQ configured: mode=%s int_window=%d zoom=%d thresholds=%s pileup_int=%d pileup_rej=%s",
        cfg.acquisition_mode,
        cfg.integration_window,
        cfg.zoom_division,
        cfg.thresholds,
        cfg.pileup_integration_time,
        cfg.enable_pileup_rejection,
    )

# similar to waveform_test.py written by Willy
def collect_waveforms(dbi, n_waveforms: int):
    logging.info(f"Collecting {n_waveforms} waveforms")
    apply_daq_mode(dbi, "waveform")

    dbi.recalibrate_baseline()
    dbi.send(START)
    time.sleep(1)
    dbi.flush(128)
    
    waveforms = []
    timeout = 5  # seconds
    t_last_packet = time.time()
    
    while len(waveforms) < n_waveforms:
        if time.time() - t_last_packet > timeout:
            logging.error("Waveform acquisition timed out")
            break
        try:
            data = dbi.recv()
        except BlockingIOError:
            continue
        
        if data[:2] == WAVEFORM_HEADER:
            t_last_packet = time.time()
            decoded = parse_waveform_packet(data)
            counters["waveform"] += 1
            if decoded['channel'] == 0:
                waveforms.append(decoded["data"])
                t_last_packet = time.time()
        elif data[0] == 0x03:
            counters["stale_ack"] += 1
        else:
            counters["unknown"] += 1

    dbi.flush()
    safe_stop(dbi)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    np.savetxt(LOG_DIR / f'waveforms_{ts}.txt', waveforms)
    logging.info(f"Saved {len(waveforms)} waveforms to {LOG_DIR / f'waveforms_{ts}.txt'}")

# also similar to testing.ipynb by Willy
def collect_spectra(dbi, n_spectra: int):
    logging.info(f"Collecting {n_spectra} spectra...")

    apply_daq_mode(dbi, 'spectrum')

    dbi.send(START)
    time.sleep(1)
    dbi.flush(64) # why 64????

    spectra = []
    timeout = 5  # seconds
    t_last_packet = time.time()

    while len(spectra) < n_spectra:
        if time.time() - t_last_packet > timeout:
            logging.error("Spectrum acquisition timed out")
            break
        try:
            data = dbi.recv()
        except BlockingIOError:
            continue

        try:
            spec = parse_spectrum_packet(data)
            counters["spectrum"] += 1
            spectra.append(spec[0])
            t_last_packet = time.time()
        except Exception:
            counters["unknown"] += 1

    dbi.flush()
    safe_stop(dbi)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    np.savetxt(LOG_DIR / f'spectra_{ts}.txt', spectra)
    logging.info(f"Saved {len(spectra)} spectra to {LOG_DIR / f'spectra_{ts}.txt'}")

def science_mode(dbi):
    global current_mode
    current_mode = Mode.SCIENCE
    logging.info('Entered SCIENCE mode')
    for daq_mode, counts in data_counts:
        if daq_mode == "waveform":
            collect_waveforms(dbi, counts)
        elif daq_mode == "spectrum":
            collect_spectra(dbi, counts)

    enter_idle(dbi)

def main():
    logging.info("Starting DAQ")
    dbi = DaqBoxInterface()
    startup_mode(dbi)

    try:
        enter_idle(dbi)
        science_mode(dbi)
    except Exception as e:
        logging.exception('DAQ task failed')
    finally:
        safe_stop(dbi)


if __name__ == "__main__":
    main()