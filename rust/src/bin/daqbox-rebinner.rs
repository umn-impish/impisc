use std::net::{SocketAddr, UdpSocket};

const NUM_CHAN: usize = 4;

fn parse_rebin_edges(bins: &String) -> Vec<u16> {
    bins.split("-")
        .into_iter()
        .map(|b| {
            b.parse::<u16>()
                .expect("Must be able to parse energy bin edge")
        })
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
            Err(e) => std::panic::panic_any(format!("Problem with receiving on rebinner: {e:?}")),
        };

        // DAQBOX packet plus header
        const TIME_INFO_SZ: usize = 5;
        const DAQBOX_PACKET_SZ: usize = 8000;
        if received != (TIME_INFO_SZ + DAQBOX_PACKET_SZ) {
            // Ignore malformed packets
            continue;
        }

        // Discard the timing info and parse the spectrum packet
        let spectra = parse_daqbox_spectrum(&buf[TIME_INFO_SZ..]);

        // Sum it up
        for (spec_idx, this_spec) in spectra.iter().enumerate() {
            for bin_idx in 0..(rebin_edges.len() - 1) {
                let a = rebin_edges[bin_idx] as usize;
                let b = rebin_edges[bin_idx + 1] as usize;
                let this_bin: u32 = this_spec[a..b].iter().map(|&x| x as u32).sum();
                sum_bins[spec_idx][bin_idx] += this_bin;
            }
        }

        // Forward it
        accumulated = (accumulated + 1) % spectra_per_packet;
        if accumulated == 0 {
            // Enough space for timestamp plus summed bins
            let mut packet: Vec<u8> =
                Vec::with_capacity(TIME_INFO_SZ + NUM_CHAN * cleared_bins[0].len());
            // The first 5 bytes are the most recent timestamp
            // and DAQBOX frame number
            packet.extend(&buf[..TIME_INFO_SZ]);
            for spec in sum_bins {
                for bin in spec {
                    packet.extend(bin.to_le_bytes());
                }
            }

            match my_sock.send_to(&packet, dest) {
                Ok(_) => {}
                Err(e) => eprintln!("Error sending packet: {e:?}"),
            };

            // Clear the accumulated packet data
            sum_bins = cleared_bins.clone();
        }
    }
}
