import time
import json
import queue
import shutil
import logging
from pathlib import Path
from enum import Enum, auto
from multiprocessing import Process, Queue

from impisc.et_daqbox.daq_box_api import DaqBoxConfig, DaqBoxInterface, START, STOP, WAVEFORM_HEADER, parse_spectrum_packet, parse_waveform_packet

import udp_sender as udp_sender
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
        self.spectra1, self.spectra2 = [], []
        self.spectra3, self.spectra4 = [], []
        self.quicklook_spectra = []
        self.waveforms = {}
        self.waveforms1, self.waveforms2 = [], []
        self.waveforms3, self.waveforms4 = [], []
        self.save_requested = False
        self.last_save = time.time()
        self.last_packet_time = None
        self.total_deadtime = 0.0
        self.last_acq_time = None  # for livetime

##################################### functions ####################################

def load_active_config() -> dict:
    with open(ACTIVE_CFG) as f:
        return json.load(f)

def enter_safe(dbi, state, reason="unknown"):
    logging.info(f"Entering safe mode, reason: {reason} \n")
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

    enter_safe(dbi, state, reason="reconfiguring DAQ")

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
    time.sleep(0.001)
    dbi.flush(128 if data_mode == "waveform" else 64)

######################################## Data receive/send ########################################

science_queue = Queue(maxsize=10000)
quicklook_queue = Queue(maxsize=10000)

def recv_science(dbi):
    """
    Receive and queue multidimensional spectra for science + quicklook
    """
    try:
        data = dbi.recv()
    except BlockingIOError:
        return False
    
    if data[:2] != WAVEFORM_HEADER: # waveform not needed for science mode
        try:
            spec = parse_spectrum_packet(data)
            try:
                science_queue.put_nowait(spec)
            except queue.Full:
                logging.warning("Science queue full, dropping packet")

            try:
                quicklook_queue.put_nowait(spec)
            except queue.Full:
                logging.warning("Quicklook queue full, dropping packet")
        except Exception:
            logging.exception("Failed to parse spectrum packet")

    return True

def recv_debug(dbi, state, buffer: DataBuffer):
    """
    Receive, classify one data packet and buffer for debug
    """
    try:
        data = dbi.recv()
    except BlockingIOError:
        return False
    
    if data[:2] == WAVEFORM_HEADER:
        try:
            decoded = parse_waveform_packet(data)
            ch = decoded["channel"] + 1
            buffer.waveforms.setdefault(ch, []).append(decoded["data"])

            # target_list = getattr(buffer, f"waveforms{ch}")
            # target_list.append(decoded["data"])
        except Exception as e:
            logging.exception("Failed to parse waveform packet")

    else:
        try:
            spec = parse_spectrum_packet(data)
            buffer.spectra.append(spec)
            # buffer.spectra1.append(spec[0])
            # buffer.spectra2.append(spec[1])
            # buffer.spectra3.append(spec[2])
            # buffer.spectra4.append(spec[3])
        except Exception:
            pass

    return True
    
def send_debug(buffer: DataBuffer):
    n_w, n_s = 0, 0 
    
    if buffer.waveforms:
        # n_w = len(buffer.waveforms)
        n_w = sum(len(wf) for wf in buffer.waveforms.values())
        udp_sender.send_udp_data(buffer.waveforms, "waveforms", dtype_code="f")
        buffer.waveforms.clear()
        time.sleep(0.005)

    if buffer.spectra:
        n_s = len(buffer.spectra)
        udp_sender.send_udp_data(buffer.spectra, "spectra", dtype_code="I")
        buffer.spectra.clear()

    logging.info(f"Sent {n_w} waveforms and {n_s} spectra via UDP\n")


############################### Acquisition modes ##################################

science_block = 2*60*32 # accummulates for 2 mins
quicklook_block = 4*32 # accumulates for 4 secs

def science_send(science_queue):
    buffers = []
    while True:
        try:
            try:
                data = science_queue.get(timeout=10.0)
                buffers.append(data)
            except queue.Empty:
                continue

            if len(buffers) >= science_block:
                udp_sender.send_udp_data(buffers, f"spectra", dtype_code="I")
                logging.info(f"Sent {len(buffers)} spectra via UDP and saved to file\n")
                buffers.clear()
        except Exception as e:
            logging.exception("Science sender crashed")

def quicklook_send(quicklook_queue):
    import quicklook_cmd

    accumulators = QuicklookAccumulator(n_spectra_per_quicklook=128, fps=32)

    while True:
        
        try:
            try:
                data = quicklook_queue.get(timeout=10.0)
                packet = accumulators.push(data)
            except queue.Empty:
                continue

            if packet is not None:
                quicklook_cmd.send_quicklook(packet)
        except Exception as e:
            logging.exception("Quicklook sender crashed")


def run_debug(dbi, state, buffer, n_waveform: int, n_spectrum: int):
    logging.info(f'Entered DEBUG mode: {n_waveform} waveforms and {n_spectrum} spectra')

    timeout = 60  # seconds
    t_last_packet = time.time()
    
    start_acquisition(dbi, state, "waveform")
    while not buffer.waveforms or any(len(wf) < n_waveform for wf in buffer.waveforms.values()):
        # check ot see if the channels are complete depending on active number of channels
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        received = recv_debug(dbi, state, buffer)
        if received:
            t_last_packet = time.time()
    enter_safe(dbi, state, 
               reason=f"{n_waveform} waveforms acquisition complete from {len(list(buffer.waveforms.keys()))} channels\n")

    start_acquisition(dbi, state, "spectrum")
    while len(buffer.spectra) < n_spectrum:
        if time.time() - t_last_packet > timeout:
            enter_safe(dbi, state, reason="DAQ timeout")
            break
        receivedd = recv_debug(dbi, state, buffer)
        if receivedd:
            t_last_packet = time.time()
    enter_safe(dbi, state, reason=f"{n_spectrum} spectra acquisition complete \n")

    send_debug(buffer)

def run_science_step(dbi):
    recv_science(dbi)

def run_science(dbi, state):
    """
    To be called continuously/repeatedly in science mode
    """
    assert state.mode == Mode.SCIENCE

    while state.mode == Mode.SCIENCE:
        if not recv_science(dbi):
            time.sleep(0.005)


    

############################### Main ########################################

def main():
    logging.info("Starting DAQ")

    dbi = DaqBoxInterface()
    state = DAQstate()
    buffer = DataBuffer()
    
    state.mode = Mode.SAFE
    logging.info("Initial mode: SAFE")

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
                run_science_step(dbi)
            except Exception as e:
                enter_safe(dbi, state, f"Science failure: {e}")

        time.sleep(0.001)

if __name__ == "__main__":

    science_proc = Process(target=science_send, args=(science_queue,), daemon=True)
    quicklook_proc = Process(target=quicklook_send, args=(quicklook_queue,), daemon=True)
    
    science_proc.start()
    quicklook_proc.start()

    main()