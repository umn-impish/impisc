import time
import json
import shutil
import logging
import datetime
import numpy as np
from pathlib import Path
from enum import Enum, auto

from impisc.et_daqbox.daq_box_api import DaqBoxConfig, DaqBoxInterface, START, STOP, WAVEFORM_HEADER, parse_spectrum_packet, parse_waveform_packet

import udp_sender
import quicklook_cmd
import receive_cmd as rcmd
from quicklook_acc import QuicklookAccumulator


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
    DEBUG = auto()
    SCIENCE = auto()

class DAQstate():
    def __init__(self):
        self.mode = Mode.SAFE
        self.last_cmd_time = None

class DataBuffer():
    def __init__(self):
        self.spectra = []
        self.quicklook_spectra = []
        self.waveforms = []
        self.save_requested = False
        self.last_save = time.time()

##################################### functions ####################################

def load_active_config() -> dict:
    with open(ACTIVE_CFG) as f:
        return json.load(f)

def enter_safe(dbi, state, reason="unknown"):
    logging.info(f"Entering safe mode, reason: {reason}")
    try:
        dbi.flush()
        dbi.send(STOP, expect_handshake=False)
        dbi.flush()
        time.sleep(0.5)
    except Exception:
        pass
    state.mode = Mode.SAFE

def configure_daq(dbi, state, data_mode: str):
    cfg_dict = load_active_config()

    if data_mode not in cfg_dict['modes']:
        raise RuntimeError(f'Unknown DAQ mode: {data_mode}')

    merged = cfg_dict['global'].copy()
    merged.update(cfg_dict['modes'][data_mode])

    enter_safe(dbi, state, reason="reconfiguring DAQ") # check if this can be removed

    cfg = DaqBoxConfig()

    for key, val in merged.items():
        if key not in DaqBoxConfig._SAVE_ATTRS:
            raise ValueError(f"DaqBoxConfig has no attribute '{key}'")
        setattr(cfg, key, val)

    dbi.send(cfg.to_packet())
    logging.info(f"Configured DAQ for mode: {data_mode}")
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

def start_acquisition(dbi: DaqBoxInterface, state, data_mode: str):
    configure_daq(dbi, state, data_mode)

    if data_mode == "waveform":
        dbi.recalibrate_baseline()

    dbi.send(START)
    time.sleep(1)
    dbi.flush(128 if data_mode == "waveform" else 64)

######################################## Data saving ########################################

def recv_once(dbi, state, buffer):
    """
    Receive and classify one data packet
    """
    try:
        data = dbi.recv()
    except BlockingIOError:
        return

    if data[:2] == WAVEFORM_HEADER:
        decoded = parse_waveform_packet(data)
        if decoded['channel'] == 0:
            buffer.waveforms.append(decoded["data"])
    else:
        try:
            spec = parse_spectrum_packet(data)
            buffer.spectra.append(spec[0])
            buffer.quicklook_spectra.append(spec[0]) if state.mode == Mode.SCIENCE else None
        except Exception:
            pass

    # logging.info(f"Buffer sizes: {len(buffer.waveforms)} waveforms, {len(buffer.quicklook_spectra)} spectra")

##################################### Saving and UDP #####################################

def save_science(buffer: DataBuffer):
    if not buffer.waveforms and not buffer.spectra:
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if buffer.waveforms:
        arr = np.array(buffer.waveforms)
        np.save(LOG_DIR / f'waveforms_{ts}.npy', arr)
        with open(LOG_DIR/f'waveforms_{ts}.bin', 'wb') as f:
            f.write(arr.tobytes())
        np.savez_compressed(LOG_DIR / f'waveforms_{ts}.npz', arr)
        buffer.waveforms.clear()

    if buffer.spectra:
        arr = np.array(buffer.spectra)
        np.save(LOG_DIR / f'spectra_{ts}.npy', arr)
        with open(LOG_DIR/f'spectra_{ts}.bin', 'wb') as f:
            f.write(arr.tobytes())
        np.savez_compressed(LOG_DIR / f'spectra_{ts}.npz', arr)
        buffer.spectra.clear()

    buffer.last_save = time.time()
    buffer.save_requested = False
    logging.info("Science data saved as .npy and .bin \n")      

def send_debug(buffer: DataBuffer):
    if buffer.waveforms:
        udp_sender.send_udp_data(np.array(buffer.waveforms), "waveforms")
        time.sleep(0.1)

    if buffer.spectra:
        udp_sender.send_udp_data(np.array(buffer.spectra), "spectra")


############################### Acquisition modes ##################################


def run_debug(dbi, state, buffer, n_waveform: int, n_spectrum: int):
    logging.info(f'Entered DEBUG mode: {n_waveform} waveforms and {n_spectrum} spectra')

    timeout = 60  # seconds
    t_last_packet = time.time()
    
    start_acquisition(dbi, state, "waveform")
    while len(buffer.waveforms) < n_waveform:
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        recv_once(dbi, state, buffer)
        t_last_packet = time.time()
    enter_safe(dbi, state, reason="waveform acquisition complete \n")

    start_acquisition(dbi, state, "spectrum")
    while len(buffer.spectra) < n_spectrum:
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        recv_once(dbi, state, buffer)
        t_last_packet = time.time()
    enter_safe(dbi, state, reason='spectra acquisition complete \n')


    send_debug(buffer)

    save_science(buffer)

def run_science(dbi, state, buffer, quicklook=None):
    """
    To be called continuously/repeatedly in science mode
    Receives and save data (under given conditions)
    Also sends quicklook data
    """
    assert state.mode == Mode.SCIENCE

    recv_once(dbi, state, buffer)

    if quicklook and buffer.quicklook_spectra:
        for spectrum in buffer.quicklook_spectra:
            result = quicklook.push(spectrum)
            if result:
                quicklook_cmd.send_quicklook(
                    result['adc_ranges'],
                    result['counts_per_range'].tolist(), 
                    result['count_rate_per_sec'].tolist(), 
                    result['num_seconds']
                )
        buffer.quicklook_spectra.clear()

    if buffer.save_requested or (time.time() - buffer.last_save > 60):
        save_science(buffer)


############################### Main ########################################

def main():
    logging.info("Starting DAQ")

    dbi = DaqBoxInterface()
    state = DAQstate()
    buffer = DataBuffer()
    quicklook = QuicklookAccumulator(n_spectra_per_quicklook=128, fps=32)
    
    state.mode = Mode.SAFE

    cmd_sock = rcmd.setup_command_socket()

    while True:
        cmd, addr = rcmd.update_flight_mode(cmd_sock)

        if cmd and addr:
            state.last_cmd_time = time.time()
            mode = cmd.get('mode')
            logging.info(f"Received command: {cmd.get('cmd')} to {mode} mode")
            
            if cmd.get("cmd") == 'set_mode' and mode == 'debug':
                state.mode = Mode.DEBUG
                params = cmd.get("params", {})
                rcmd.send_ack(cmd_sock, addr, cmd, "accepted debug request", state.mode)

                run_debug(dbi, state, buffer, params.get('n_waveforms', 3000), params.get('n_spectra', 320))
            
            elif cmd.get("cmd") == 'set_mode' and mode == 'science':
                start_acquisition(dbi, state, "spectrum")
                state.mode = Mode.SCIENCE
                rcmd.send_ack(cmd_sock, addr, cmd, "science started", state.mode)

            else:
                rcmd.send_ack(cmd_sock, addr, cmd, "invalid mode", state.mode)

        if state.mode == Mode.SCIENCE:
            try:
                run_science(dbi, state, buffer, quicklook=quicklook)
            except Exception as e:
                enter_safe(dbi, state, f"Science failure: {e}")

        time.sleep(0.05)

if __name__ == "__main__":
    main()