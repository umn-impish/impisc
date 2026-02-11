# execute with python -m scripts.tests.test_daq_control
import time
import logging
import datetime
import numpy as np
from time import sleep
from pathlib import Path
from impisc.et_daqbox.daq_box_api import DaqBoxConfig, DaqBoxInterface, START, STOP, WAVEFORM_HEADER, parse_spectrum_packet, parse_waveform_packet

def print_help():
    print("""
        DAQ control commands:
          recalibrate                         Recalibrate the DAQ system
          flush                               Flush DAQ packets
          recv                                Receive packet
          recv_waveform N                     Receive N waveform packets
          recv_spectrum N                     Receive N spectrum packets
          help                                Show this help message
          quit / exit                         Quit the application
        """)

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "impish_logs"
print("Logging into:", LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR/"daq.log"
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE),
                              logging.StreamHandler()])

cfg_files = {
    "waveform": SCRIPT_DIR / "waveform_config.json",
    "spectrum": SCRIPT_DIR / "spectrum_config.json",
}
counters = {
    "waveform": 0,
    "spectrum": 0,
    "stale_ack": 0,
    "unknown": 0,
}


def safe_stop(dbi):
    try:
        dbi.send(STOP)
    except Exception:
        pass
    try:
        dbi.flush()
    except Exception:
        pass

def load_config(dbi, mode: str):
    """
    Load configuration parameters
    """
    cfg_file = cfg_files.get(mode)
    if cfg_file is None or not cfg_file.exists():
        raise RuntimeError(f"Missing config file for {mode} mode")
    
    safe_stop(dbi)

    cfg = DaqBoxConfig.from_file(cfg_file)

    dbi.send(cfg.to_packet())
    dbi.flush()

    logging.info(f"DAQ configured for {mode} mode")

# similar to waveform_test.py written by Willy
def collect_waveforms(dbi, n_waveforms: int):
    print(f"Collecting {n_waveforms} waveforms ...")
    dbi.send(STOP)
    load_config(dbi, 'waveform')

    dbi.recalibrate_baseline()
    dbi.send(START)
    time.sleep(1)
    dbi.flush(128)
    
    waveforms = []
    timeout = 5  # seconds
    t_last_packet = time.time()
    
    while len(waveforms) < n_waveforms: # 3000 was used, why???
        if time.time() - t_last_packet > timeout:
            logging.error("Waveform acquisition timed out")
            break
        try:
            data = dbi.recv()
        except BlockingIOError:
            continue
        
        if data[0] == 0x03:
            counters["stale_ack"] += 1
            continue
        elif data[:2] == WAVEFORM_HEADER:
            decoded = parse_waveform_packet(data)
            counters["waveform"] += 1
            if decoded['channel'] == 0:
                waveforms.append(decoded["data"])
                t_last_packet = time.time()
        else:
            counters["unknown"] += 1

    dbi.flush()
    safe_stop(dbi)

    # print(waveforms[10])
    # print('Waveform acquisition complete')
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    np.savetxt(LOG_DIR / f'waveforms_{ts}.txt', waveforms)
    print(f"Saved {len(waveforms)} waveforms to {LOG_DIR / f'waveforms_{ts}.txt'}")

# also similar to testing.ipynb by Willy
def collect_spectra(dbi, n_spectra: int):
    print(f"Collecting {n_spectra} spectra...")

    load_config(dbi, 'spectrum')

    dbi.send(STOP)
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

        if data[:2] == WAVEFORM_HEADER:
            counters["unknown"] += 1
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

    # print("Spectrum acquisition complete")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    np.savetxt(LOG_DIR / f'spectra_{ts}.txt', spectra)
    print(f"Saved {len(spectra)} spectra to {LOG_DIR / f'spectra_{ts}.txt'}")

def main():
    print("Connecting to DAQ box interface...")
    logging.info("Starting DAQ")
    dbi = DaqBoxInterface()
    print("DAQ ready. Type 'help' for commands.")

    while True:
        try:
            cmd = input("daq: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting DAQ... ")
            safe_stop(dbi)
            break

        if cmd in ("quit", "exit"):
            print("Exiting...")
            try:
                safe_stop(dbi)
            except Exception:
                pass
            break
        
        elif cmd == "help":
            print_help()

        elif cmd == "recalibrate":
            print("Recalibrating baseline...")
            dbi.recalibrate_baseline()
        elif cmd == "flush" :
            dbi.flush()
            print("Sockets flushed")

        elif cmd == "recv":
            try:
                packet = dbi.recv()
            except BlockingIOError:
                print("No data to receive")
                continue
            
            if packet.startswith(WAVEFORM_HEADER):
                wf_data = parse_waveform_packet(packet)
                print(f"Waveform data received with channel {wf_data['channel']}, timestamp {wf_data['timestamp']}, length {len(wf_data['data'])}")
            else:
                spec_data = parse_spectrum_packet(packet)
                print(f"Spectrum data received")
        elif cmd.startswith("recv_waveform"):
            parts = cmd.split()
            if len(parts) != 2:
                print("Type: recv_waveform N")
                continue
            collect_waveforms(dbi, int(parts[1]))

        elif cmd.startswith("recv_spectrum"):
            parts = cmd.split()
            if len(parts) != 2:
                print("Type: recv_spectrum N")
                continue            
            collect_spectra(dbi, int(parts[1]))

        else:
            print("Unkown command, type 'help' for commands")

    logging.info("DAQ packet summary:")
    for k, v in counters.items():
        logging.info("Packets %s: %d", k, v)



if __name__ == "__main__":
    main()