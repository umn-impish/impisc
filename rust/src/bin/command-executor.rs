/*
    A command executor program.

    Accepts an arbitrary command via UDP socket.
    Max length is 1024B long.

    Command is executed using `bash -sl` (see man bash)

    stdout and stderr are captured and sent back separately.
    packets are broken into 1024B chunks, and the 1025th byte
    indicates the packet "sequence number".
*/

use std::net::{SocketAddr, UdpSocket};
use std::process::{Command, Output, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};
// Impl's needed for writing onto stdio of process
use std::io::Write;

/* OutputWrapper wraps a process result
  into a nice struct. Its stderr field
  can also capture the _shell_ stderr in case
  of some kind of OS error getting thrown before
  or during execution.
*/
struct OutputWrapper {
    cmd: Vec<u8>,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    status_code: i32,
}

impl OutputWrapper {
    fn from(cmd: String, proc_out: Output) -> OutputWrapper {
        return OutputWrapper {
            cmd: cmd.into_bytes(),
            stdout: proc_out.stdout.into(),
            stderr: proc_out.stderr.into(),
            status_code: proc_out.status.code().unwrap_or(-1),
        };
    }

    fn to_packet(&self) -> Vec<u8> {
        // ASCII group separator nonprintable character
        const GROUP_SEP: u8 = 0x1D;

        let mut response = Vec::new();
        response.push(self.status_code as u8);
        response.push(GROUP_SEP);
        response.extend(self.cmd.iter());
        response.push(GROUP_SEP);
        response.extend(self.stdout.iter());
        response.push(GROUP_SEP);
        response.extend(self.stderr.iter());
        return response;
    }
}

fn main() {
    // Where do we send output?
    let dest_port = std::env::var("HEADER_STAMPER_PORT")
        .expect("Need HEADER_STAMPER_PORT to be set")
        .parse::<u16>()
        .expect("Need HEADER_STAMPER_PORT to be a parsable u16");
    let send_to_me = format!("127.0.0.1:{dest_port}");

    // Where do we receive commands?
    let listen_port = std::env::var("COMMAND_EXECUTOR_PORT")
        .expect("Need COMMAND_EXECUTOR_PORT to be set")
        .parse::<u16>()
        .expect("Need COMMAND_EXECUTOR_PORT to be a parsable u16");

    // Special address 0000 is like INADDR_ANY.
    let sock = UdpSocket::bind(format!("0.0.0.0:{listen_port}"))
        .expect("Need to be able to bind socket to given listen port.");
    sock.set_read_timeout(None)
        .expect("Need to be able to set socket timeout");

    // Count how many packets we receive for bookkeeping on the ground
    let mut packets_received: u8 = 0;
    loop {
        let Some((cmd, _)) = receive_command(&sock) else {
            eprintln!("Failed to parse command from UDP packet.");
            continue;
        };
        packets_received += 1;

        // If there is a problem executing part of the command,
        // put the error msg into the wrapper stderr
        let res = match execute(&cmd) {
            Ok(r) => r,
            Err(e) => OutputWrapper {
                cmd: cmd,
                stdout: vec![],
                stderr: format!("{e:?}").into_bytes(),
                status_code: -1,
            },
        };

        reply_with(&res, &sock, &packets_received, &send_to_me);
    }
}

/// Reply to the given socket with the results in OutputWrapper.
/// the reply format is to split up
/// stdout and stderr with a header
/// indicating if the command worked or not.
///
/// Packet format:
/// ```
/// (u32 timestamp) + (u8 num cmds received) + (u16 packet order) + (u16 total number of reply packets) + (512x u8 response data)
/// ```
fn reply_with(res: &OutputWrapper, sock: &UdpSocket, num_cmds_received: &u8, send_to_me: &String) {
    // slice response up into chunks and send it off
    let res_bytes = res.to_packet();
    const STEP: usize = 512;
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("time should go forward")
        .as_secs() as u32;
    let total_packets: u16 = res_bytes.len().div_ceil(STEP) as u16;
    for i in (0..res_bytes.len()).step_by(STEP) {
        // Go until the end of data or the step size
        let max_idx = std::cmp::min(res_bytes.len(), i + STEP);
        // Put the response bytes first so we can pad it easily
        let mut send_bytes = res_bytes[i..max_idx].to_vec();
        if send_bytes.len() != STEP {
            let padding: usize = STEP - send_bytes.len();
            send_bytes.extend(std::iter::repeat_n(0u8, padding));
        }

        // Put the timestamp at the front of the packet
        send_bytes.extend(timestamp.to_le_bytes());
        // Put the command counter
        send_bytes.push(*num_cmds_received);
        // Put the packet ordering
        let packet_ordering = (i / STEP) as u16;
        send_bytes.extend(packet_ordering.to_le_bytes());
        // Put the total number of packets we'll get
        send_bytes.extend(total_packets.to_le_bytes());

        sock.send_to(&send_bytes, &send_to_me).expect("failed to send UDP response");
        // Delay a short while to not overwhelm the network stack
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
}

/// Receive a command as a series of bytes from a socket.
/// Returns a tuple (cmd, sender address).
fn receive_command(sock: &UdpSocket) -> Option<(Vec<u8>, SocketAddr)> {
    // The command can be up to 8192 bytes long
    // Any longer gets dropped
    let mut buf = [0; 8192];
    let (num_recv, sender) = sock.recv_from(&mut buf).ok()?;

    // Drop empty bytes from the buffer
    let vecta = buf[..num_recv].to_vec();
    return Some((vecta, sender));
}

/// Execute a command given as a string as a subprocess
/// in a shell.
/// The shell is invoked as `bash -l -s` and the
/// command is piped to its stdin;
/// its stdout and stderr are captured separately.
/// In this way, typical shell syntax and nicities
/// like loops, redirection, and pipes may be used.
fn execute(cmd: &Vec<u8>) -> std::io::Result<OutputWrapper> {
    let mut command = Command::new("bash")
        .arg("-ls")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    if let Some(mut stdin) = command.stdin.take() {
        stdin.write_all(cmd)?;
    }

    let out = command.wait_with_output()?;
    let cmd_str = String::from_utf8(cmd.clone()).unwrap();
    return Ok(OutputWrapper::from(cmd_str, out));
}
