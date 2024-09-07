use clap::{Parser, ArgGroup};
use std::net::SocketAddr;
use std::option::Option;

/*
 * Here we define the command line args used by udpcapture.
 * Optional args are (logically) annotated, and helpful
 * messages are printed as part of the usage.
 * */

#[derive(Parser)]
// Enforce either file name or forwarding addrs given
#[command(group(
    ArgGroup::new("outputs")
        .required(true)
        .args(&["base_filename", "post_process_cmd"])
))]
// Info on the command itself
#[command(
    version="1.0",
    about="Capture UDP packets and save them to files, and/or forward them.",
    long_about=None
)]
pub struct ProgramArgs {
    #[arg(short='p', long, help="UDP port to listen on, in host representation")]
    pub port: u16,
    #[arg(short='t', long, help="Time between packets to wait before closing file (seconds)")]
    pub time_between_packets: Option<u16>,
    #[arg(short='l', long,
          help="Maximum file lifetime before close (seconds)",
          requires="file_lifetime")]
    pub file_lifetime: Option<u16>,
    #[arg(short='b', long,
          help="Initial part of output file name.")]
    pub base_filename: Option<String>,
    #[arg(short='c', long,
          help="Command to run on $out_file after it is closed.",
          group="outputs")]
    pub post_process_cmd: Option<String>,
    #[arg(short='f', long,
          help="Many IPv4 address to forward data to, in the format addr:port",
          group="outputs")]
    pub forward_addrs: Option<Vec<SocketAddr> >
}

