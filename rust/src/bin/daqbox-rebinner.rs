use std::net::{SocketAddr, UdpSocket};

const NUM_CHAN: usize = 4;

fn parse_rebin_edges(bins: &String) -> Vec<u16> {
    bins.split("-")
        .into_iter()
        .map(|b| b.parse::<u16>().expect("Must be able to parse QL bin edge"))
        .collect()
}

fn parse_daqbox_spectrum(data: &[u8]) -> [[u16; 1000]; 4] {
    /* Parse the 8000B DAQBOX spectrum packet into a 4x1000 u16 2-dimensional array */
    let mut ret: [[u16; 1000]; NUM_CHAN] = [[0; 1000]; NUM_CHAN];
    for i in (0..data.len()).step_by(8) {
        for chan in 0..4 {
            let start = i + chan * 2;
            // 2B per channel
            ret[chan][i / (2 * NUM_CHAN)] = (data[start] as u16) * 256 + (data[start + 1] as u16);
        }
    }
    ret
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != (1 + 4) {
        let name = &args[0];
        std::panic::panic_any(format!("Usage: {name} <recv_port> <dest_port> <num frames to sum over> <ADC edges for rebinning>"))
    }

    let parse_u16 = |v: &String, msg: &str| v.parse::<u16>().expect(msg);
    let spectra_per_packet = parse_u16(&args[3], "Number of frames to sum must be valid u16");

    let dest_port = parse_u16(&args[2], "Destination port must be u16");
    let dest = SocketAddr::from(([127, 0, 0, 1], dest_port));

    let listen_port = parse_u16(&args[1], "Listen port must be u16");
    let my_sock = UdpSocket::bind(format!("0.0.0.0:{listen_port}"))
        .expect("Need to be able to bind UDP listen socket");

    let rebin_edges = parse_rebin_edges(&args[4]);

    let cleared_bins: Vec<Vec<u32>> = vec![vec![0; rebin_edges.len() - 1]; NUM_CHAN];
    let mut sum_bins = cleared_bins.clone();
    let mut accumulated: u16 = 0;
    loop {
        // Accept data
        const BUF_SZ: usize = 8005;
        let mut buf: [u8; BUF_SZ] = [0; BUF_SZ];
        let received = match my_sock.recv(&mut buf) {
            Ok(v) => v,
            Err(e) => std::panic::panic_any(format!("Problem with receiving on quicklook: {e:?}")),
        };

        // DAQBOX packet plus header
        if received != 8005 {
            // Ignore malformed packets
            continue;
        }

        // Discard the timing info and parse the spectrum packet
        let spectra = parse_daqbox_spectrum(&buf[5..]);

        // Sum it up
        for spec_idx in 0..spectra.len() {
            for bin_idx in 0..(rebin_edges.len() - 1) {
                let a = rebin_edges[bin_idx] as usize;
                let b = rebin_edges[bin_idx + 1] as usize;
                let this_bin: u32 = spectra[spec_idx][a..b].iter().map(|&x| x as u32).sum();
                sum_bins[spec_idx][bin_idx] += this_bin;
            }
        }

        // Forward it
        accumulated = (accumulated + 1) % spectra_per_packet;
        if accumulated == 0 {
            let tstamp = std::time::SystemTime::now()
                .duration_since(std::time::SystemTime::UNIX_EPOCH)
                .expect("System time must be after unix epoch")
                .as_secs() as u32;

            // Enough space for timestamp plus QL bins
            let mut packet: Vec<u8> = Vec::with_capacity(
                4 + cleared_bins.len() * cleared_bins[0].len()
            );
            packet.extend(tstamp.to_le_bytes());
            for spec in sum_bins {
                for bin in spec {
                    packet.extend(bin.to_le_bytes());
                }
            }

            match my_sock.send_to(&packet, dest) {
                Ok(_) => {}
                Err(e) => eprintln!("Error sending packet: {e:?}"),
            };

            // Clear the quicklook packet data
            sum_bins = cleared_bins.clone();
        }
    }
}
