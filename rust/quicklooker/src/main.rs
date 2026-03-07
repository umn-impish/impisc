use std::net::{SocketAddr, UdpSocket};

const NUM_QLOOK: usize = 4;
const NUM_CHAN: usize = 4;

fn parse_rebin_edges(envar_name: &str) -> Vec<u16> {
    std::env::var(envar_name)
        .expect(format!("{envar_name} needs to be set").as_str())
        .split("-")
        .into_iter()
        .map(|b| b.parse::<u16>().expect("Must be able to parse QL bin edge"))
        .collect()
}

fn parse_envar(varname: &str) -> u16 {
    std::env::var(varname)
        .expect(format!("{varname} must be set").as_str())
        .parse::<u16>()
        .expect(format!("{varname} must be a valid u16").as_str())
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
    let listen_port = parse_envar("QUICKLOOK_RECV_PORT");
    let dest_port = parse_envar("QUICKLOOK_UDPCAP_PORT");
    let sum_seconds = parse_envar("QUICKLOOK_SUM_SECONDS") as u8;

    let rebin_edges = parse_rebin_edges("QUICKLOOK_EDGES");
    const NUM_EXPECTED: usize = NUM_QLOOK + 1;
    if rebin_edges.len() != NUM_EXPECTED {
        std::panic::panic_any(format!("Need to provide {NUM_EXPECTED} bin edges"));
    }

    let dest = SocketAddr::from(([127, 0, 0, 1], dest_port));
    let my_sock = UdpSocket::bind(format!("0.0.0.0:{listen_port}"))
        .expect("Need to be able to bind UDP listen socket");

    const FRAMERATE: u8 = 32;
    let spectra_per_packet: u32 = (sum_seconds as u32) * (FRAMERATE as u32);

    let mut sum_bins: [[u32; NUM_CHAN]; NUM_QLOOK] = [[0; NUM_CHAN]; NUM_QLOOK];
    let mut accumulated: u32 = 0;
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
            let tstamp= std::time::SystemTime::now()
                .duration_since(std::time::SystemTime::UNIX_EPOCH)
                .expect("System time must be after unix epoch")
                .as_secs() as u32;

            let mut packet: Vec<u8> = tstamp.to_le_bytes().iter().map(|&x| x as u8).collect();
            for spec in sum_bins {
                for bin in spec {
                    packet.extend(bin.to_le_bytes());
                }
            }

            match my_sock.send_to(&packet, dest) {
                Ok(_) => {},
                Err(e) => eprintln!("Error sending packet: {e:?}")
            };

            sum_bins = [[0; 4]; 4];
        }
    }
}
