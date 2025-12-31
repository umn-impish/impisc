/* udpcapture: save packets to files, and forward them elsewhere.
 * Files can be operated on with a shell script afterwards.
 * Run `udpcapture --help` for more info!
 *
 * Built to work on Unix systems but should be adaptable to Windows with some
 * minor modifications.
 *
 * Useful to have this in Rust or C++ for low-resource systems (e.g. embedded, SBC)
 * Rust is nice, though, because it's safe :-)
 * */
mod args;
mod writer;
use clap::Parser;
use std::cmp::max;
use std::net::{UdpSocket, SocketAddr};
use std::process::Command;
use std::io::ErrorKind;
use std::time::Duration;

fn main() {
    let args = args::ProgramArgs::parse();
    let sock = UdpSocket::bind(format!("0.0.0.0:{}", args.port))
                         .expect("UDP socket port needs to be available to bind");

    if let Some(life) = args.file_lifetime {
        // Make the socket timeout 5x shorter
        // than the file lifetime.
        // Minimum 1s
        let timeout = max(life / 5, 1) as u64;
        sock.set_read_timeout(Some(Duration::from_secs(timeout)))
            .expect("Timeout must be a valid duration in seconds");
    }

    let mut writer = writer::FileWriter::new(
        args.base_filename, args.max_file_size,
        args.file_lifetime.unwrap_or(u16::MAX));

    loop {
        let data = receive_data(&sock);
        if let Some(saved_file) = writer.maybe_write_data(&data) {
            post_process(&args.post_process_cmd, &saved_file);
        }
        if let Some(fwds) = &args.forward_addrs {
            forward_data(&sock, &data, &fwds);
        }
    }
}

fn receive_data(sock: &UdpSocket) -> Vec<u8> {
    // Max packet size in UDP
    let mut buf = [0u8; 65535];
    let recvd = match sock.recv(&mut buf) {
        Ok(rec) => rec,
        Err(e)  => {
            if e.kind() == ErrorKind::WouldBlock {
                // Socket timed out; don't care
                // But, set the ret Vec to no size
                0
            }
            else {
                panic!("unexpected error when receiving: {e:?}")
            }
        }
    };
    return buf[..recvd].to_vec();
}

fn post_process(cmd: &Option<String>, file: &String) {
    if let Some(cmd) = cmd {
        // The file which was just written gets put into
        // the shell variable `out_file`.
        // Post-process scripts may access it as $out_file
        let full_cmd = format!("out_file={}; {}", file, cmd);
        match Command::new("bash")
                      .arg("-c")
                      .arg(&full_cmd)
                      .output() {
            Ok(op) => eprintln!("`{}` ran: {:?}", &cmd, &op),
            Err(e) => eprintln!("`{}` did not run: {:?}", &cmd, &e),
        }
    }
}

fn forward_data(
    sock: &UdpSocket,
    dat: &[u8],
    destinations: &Vec<SocketAddr>
) {
    for d in destinations.iter() {
        sock.send_to(dat, &d)
            .expect(&format!("Need to be able to send data to {:?}", d));
    }
}
