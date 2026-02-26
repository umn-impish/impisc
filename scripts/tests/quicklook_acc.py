import logging
from typing import Optional, Dict, Sequence

class QuicklookAccumulator:
    """
    Accumulate a fixed number of spectra and produces quicklook products. 
    Quicklook products are counts per range every 4 secs, count rate every seconds, num of seconds = 4
    4 seconds of data is 4*32 = 128 spectra
    """

    def __init__(self, n_spectra_per_quicklook: int = 128, fps: int = 32, adc_ranges=None):
        self.n_spectra_per_quicklook = n_spectra_per_quicklook
        self.fps = fps
        self.adc_ranges = adc_ranges or [(0, 249), (250, 599), (600, 899), (900, 1000)]
        self._buffer = []

    def reset(self):
        self._buffer.clear()
   

    def push(self, spectrum: list):
        """
        Return quicklook dictionary every 4 seconds, else None
        """
        if not hasattr(spectrum, "__len__"):
            raise ValueError(f"push() expects one spectrum (1D sequence)")

        self._buffer.append(spectrum)

        if len(self._buffer) < self.n_spectra_per_quicklook:
            return None

        data = self._buffer[:128]
        logging.info(f"Quicklook data ready: {len(data)}")
        self.reset()

        return self._compute_quicklook(data)

    def _compute_quicklook(self, spectra: list):
        """
        """
        if not spectra:
            print("Warning: No spectra data found.")
            return
        
        num_bins = len(spectra[2])
        num_channels = 4

        summed_spectra = [[sum(col) for col in zip(*rows)] for rows in zip(*spectra)]  # takes it from (128, 1000, 4) to (1000, 4)
        ch = list(zip(*summed_spectra))
 
        logging.info(f"Computing counts per range for ADC ranges: {self.adc_ranges}")

        num_seconds = self.n_spectra_per_quicklook // self.fps
        counts_per_sec = []
        total_counts_per_range = []
         
        # for sec in range(num_seconds): # 0 to 3
        #     start = sec * self.fps # 0, 32, 64, 96
        #     end = start + self.fps # 32, 64, 96, 128
        #     block = spectra[start:end] # spectra is (128, 1000, 4)
        #     spec_1sec = [[sum(col) for col in zip(*rows)] for rows in zip(*block)] # (1000, 4) 32 spectra summed up
        #     total_sums = [sum(channel) for channel in zip(*spec_1sec)] # (1 total counts in 1 sec by 4 channels)

        for n_ch in range(len(ch)):
            counts_per_range = [0] * len(self.adc_ranges) # 4 adc ranges
            spec = ch[n_ch]

            for i, (low, high) in enumerate(self.adc_ranges):
                counts_per_range[i] = sum(spec[low:high+1]) # (1 counts by 4) adc bin ranges, iterated over 4 channels
            
            total_counts_per_range.append(list(counts_per_range))
            total_counts = sum(counts_per_range)
            counts_per_sec.append(total_counts / num_seconds)
            
        return {
            "det_ebin1": self.adc_ranges[0][1],
            "det_ebin2": self.adc_ranges[1][1],
            "det_ebin3": self.adc_ranges[2][1],
            "det_ebin4": self.adc_ranges[3][1],
            "det1_ebin1_counts": int(total_counts_per_range[0][0]),
            "det1_ebin2_counts": int(total_counts_per_range[0][1]),
            "det1_ebin3_counts": int(total_counts_per_range[0][2]),
            "det1_ebin4_counts": int(total_counts_per_range[0][3]),
            
            "det2_ebin1_counts": int(total_counts_per_range[1][0]),
            "det2_ebin2_counts": int(total_counts_per_range[1][1]),
            "det2_ebin3_counts": int(total_counts_per_range[1][2]),
            "det2_ebin4_counts": int(total_counts_per_range[1][3]),
            
            "det3_ebin1_counts": int(total_counts_per_range[2][0]),
            "det3_ebin2_counts": int(total_counts_per_range[2][1]),
            "det3_ebin3_counts": int(total_counts_per_range[2][2]),
            "det3_ebin4_counts": int(total_counts_per_range[2][3]),
            
            "det4_ebin1_counts": int(total_counts_per_range[3][0]),
            "det4_ebin2_counts": int(total_counts_per_range[3][1]),
            "det4_ebin3_counts": int(total_counts_per_range[3][2]),
            "det4_ebin4_counts": int(total_counts_per_range[3][3]),

            "det1_ebin1_cps": int(counts_per_sec[0]),
            "det2_ebin2_cps": int(counts_per_sec[1]),
            "det3_ebin3_cps": int(counts_per_sec[2]),
            "det4_ebin4_cps": int(counts_per_sec[3])
        }


