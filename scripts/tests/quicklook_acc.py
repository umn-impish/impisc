import logging
import numpy as np
from typing import Optional, Dict

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

    def push(self, spectrum: np.ndarray) -> Optional[Dict]:
        """
        Return quicklook dictionary every 4 seconds, else None
        """
        # logging.info(f"Pushing spectrum id={id(spectrum)}")

        if np.array(spectrum).ndim != 1:
            raise ValueError(
                f"push() expects ONE spectrum (1D), got shape {np.array(spectrum).shape}"
            )

        self._buffer.append(spectrum)

        if len(self._buffer) < self.n_spectra_per_quicklook:
            return None

        data = np.array(self._buffer)
        logging.info(f"Quicklook data ready: {data.shape}")
        self.reset()

        return self._compute_quicklook(data)

    def _compute_quicklook(self, spectra: np.ndarray) -> Dict:
        """
        spectra shape = (N, adc bins)
        """
        summed_spectrum = spectra.sum(axis=0)

        counts_per_range = np.zeros(len(self.adc_ranges), dtype=np.int64)

        logging.info(f"Computing counts per range for ADC ranges: {self.adc_ranges}")
        for i, (low, high) in enumerate(self.adc_ranges):
            counts_per_range[i] = summed_spectrum[low:high+1].sum()

        num_seconds = self.n_spectra_per_quicklook // self.fps

        spectra_trimmed = spectra[:num_seconds*self.fps]

        count_rate_per_second = spectra_trimmed.reshape(num_seconds, self.fps, -1).sum(axis=(1, 2)) # count rate


        return {
            "det1_ebin1": self.adc_ranges[0][1],
            "det1_ebin2": self.adc_ranges[1][1],
            "det1_ebin3": self.adc_ranges[2][1],
            "det1_ebin4": self.adc_ranges[3][1],
            "det1_ebin1_counts": int(counts_per_range[0]),
            "det1_ebin2_counts": int(counts_per_range[1]),
            "det1_ebin3_counts": int(counts_per_range[2]),
            "det1_ebin4_counts": int(counts_per_range[3]),
            "det1_ebin1_cps": int(count_rate_per_second[0]),
            "det1_ebin2_cps": int(count_rate_per_second[1]),
            "det1_ebin3_cps": int(count_rate_per_second[2]),
            "det1_ebin4_cps": int(count_rate_per_second[3])
        }
