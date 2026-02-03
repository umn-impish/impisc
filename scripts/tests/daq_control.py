import time
import json
import shutil
import logging
import datetime
import udp_sender
import numpy as np
from pathlib import Path
import receive_cmd as rcmd
from enum import Enum, auto
from impisc.et_daqbox.daq_box_api import DaqBoxConfig, DaqBoxInterface, START, STOP, WAVEFORM_HEADER, parse_spectrum_packet, parse_waveform_packet


###################################### Paths and logging ####################################

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "impish_logs"
CONFIG_DIR = SCRIPT_DIR / "config"
ACTIVE_CFG = CONFIG_DIR / "active.json"
DEFAULT_CFG = CONFIG_DIR / "default.json"

if not ACTIVE_CFG.exists():
    shutil.copy(DEFAULT_CFG, ACTIVE_CFG)

print("Logging into:", LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR/"daq.log"
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

#################################### states #####################################

class Mode(Enum):
    SAFE = auto()
    SCIENCE = auto()

class DAQstate():
    def __init__(self):
        self.error_count = 0
        self.mode = Mode.SAFE
        self.last_cmd_time = None

class DataBuffer():
    def __init__(self):
        self.spectra = []
        self.waveforms = []
        self.save_requested = False
        self.last_save = time.time()

counters = {
    "waveform": 0,
    "spectrum": 0,
    "stale_ack": 0,
    "unknown": 0,
}

##################################### functions ####################################

def load_active_config() -> dict:
    with open(ACTIVE_CFG) as f:
        return json.load(f)

def enter_safe(dbi, state, reason="unknown"):
    logging.error(f"Entering safe mode, reason: {reason}")
    try:
        dbi.send(STOP)
        dbi.flush()
    except Exception:
        pass

    state.mode = Mode.SAFE

def configure_daq(dbi, data_mode: str):
    """
    Apply global + daq specific config modes
    """
    cfg_dict = load_active_config()

    if data_mode not in cfg_dict['modes']:
        raise RuntimeError(f'Unknown DAQ mode: {data_mode}')

    merged = cfg_dict['global'].copy()
    merged.update(cfg_dict['modes'][data_mode])

    enter_safe(dbi, state)

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

def start_acquisition(dbi: DaqBoxInterface, mode: str):
    configure_daq(dbi, mode)

    if mode == "waveform":
        dbi.recalibrate_baseline()

    dbi.send(START)
    time.sleep(1)
    dbi.flush(128 if mode == "waveform" else 64)

def recv_once(dbi, buffer):
    """
    Receive and classify one data packet
    """

    try:
        data = dbi.recv()
    except BlockingIOError:
        return
           
    if data[:2] == WAVEFORM_HEADER:
        decoded = parse_waveform_packet(data)
        counters["waveform"] += 1
        if decoded['channel'] == 0:
            buffer.waveforms.append(decoded["data"])
    else:
        try:
            spec = parse_spectrum_packet(data)
            counters["spectrum"] += 1
            buffer.spectra.append(spec[0])
        except Exception:
            counters["unknown"] += 1


def save_data(buffer: DataBuffer):
    now = time.time()

    if not buffer.save_requested and (now - buffer.last_save < 24*60*60):
        return
    if not buffer.waveforms and not buffer.spectra:
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if buffer.waveforms:
        arr = np.array(buffer.waveforms)
        udp_sender.send_udp_data(arr, "waveforms")
        np.save(LOG_DIR / f'waveforms_{ts}.npy', buffer.waveforms) # still save to disk?
        buffer.waveforms.clear()
    if buffer.spectra:
        arr = np.array(buffer.spectra)
        udp_sender.send_udp_data(arr, "spectra")
        np.save(LOG_DIR / f'spectra_{ts}.npy', buffer.spectra) # also still save to disk?
        buffer.spectra.clear()

    buffer.last_save = time.time()
    buffer.save_requested = False
    logging.info("Science data saved and sent over UDP")          

############################### Acquisition modes ##################################

def debug_mode(dbi, state, n_waveform: int, n_spectrum: int):
    logging.info(f'Entered DEBUG mode: {n_waveform} waveforms and {n_spectrum} spectra')
    buffer = DataBuffer()

    timeout = 60  # seconds
    t_last_packet = time.time()
    
    start_acquisition(dbi, "waveform")
    while len(buffer.waveforms) < n_waveform:
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        recv_once(dbi, buffer)
        t_last_packet = time.time()
    enter_safe(dbi, state, reason="waveform acquisition complete")

    start_acquisition(dbi, "spectrum")
    while len(buffer.spectra) < n_spectrum:
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        recv_once(dbi, buffer)
        t_last_packet = time.time()
    enter_safe(dbi, state, reason='spectra acquisition complete')

    save_data(buffer)
    enter_safe(dbi, state, reason="Debug mode completed")

def run_science(dbi, state, buffer):
    """
    To be called continuously/repeatedly in science mode
    """
    recv_once(dbi, buffer)
    save_data(buffer)


############################### Main ########################################

def main():
    logging.info("Starting DAQ")

    dbi = DaqBoxInterface()
    state = DAQstate()
    buffer = DataBuffer()
    
    state.mode = Mode.SAFE

    cmd_sock = rcmd.setup_command_socket()

    while True:
        cmd, addr = rcmd.update_flight_mode(cmd_sock)

        if cmd and addr:
            state.last_cmd_time = time.time()
            logging.info(f"Received command: {cmd.get('cmd')}")
            
            if cmd.get("cmd") == 'set_mode' and cmd.get('mode') == 'debug':
                params = cmd.get("params", {})

                debug_mode(dbi, state, params.get('n_waveforms', 3000), params.get('n_spectra', 320))
                rcmd.send_ack(cmd_sock, addr, cmd, "accepted debug request", state.mode)
            
            elif cmd.get("cmd") == 'set_mode' and cmd.get('mode') == 'science':
                state.mode = Mode.SCIENCE
                start_acquisition(dbi, "waveform")
                rcmd.send_ack(cmd_sock, addr, cmd, "science started", state.mode)
            
            elif cmd.get("cmd") == "dump_data":
                buffer.save_requested = True
                rcmd.send_ack(cmd_sock, addr, cmd, "data dump scheduled", state.mode)
            else:
                rcmd.send_ack(cmd_sock, addr, cmd, "rejected", state.mode)
            
        if state.mode == Mode.SCIENCE:
            try:
                run_science(dbi, state, buffer)
            except Exception as e:
                enter_safe(dbi, state, f"Science failure: {e}")

        time.sleep(0.05)

if __name__ == "__main__":
    main()