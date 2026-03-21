/*
    A command executor program.

    Accepts an arbitrary command via UDP socket.
    Max length is 1024B long.

    Command is executed using `bash -sl` (see man bash)

    stdout and stderr are captured and sent back separately.
    packets are broken into 1024B chunks, and the 1025th byte
    indicates the packet "sequence number".
*/

use std::ffi::{OsStr, OsString};
// Unix-specific byte string decoding
use std::net::{SocketAddr, UdpSocket};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::ffi::OsStringExt;
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
    cmd: OsString,
    stdout: OsString,
    stderr: OsString,
    status_code: i32,
}

impl OutputWrapper {
    fn from(cmd: &Vec<u8>, proc_out: &Output) -> OutputWrapper {
        return OutputWrapper {
            cmd: OsString::from_vec((&cmd).to_vec()).into(),
            stdout: OsStr::from_bytes(&proc_out.stdout).into(),
            stderr: OsStr::from_bytes(&proc_out.stderr).into(),
            status_code: proc_out.status.code().unwrap_or(0),
        };
    }

    fn to_packet(&self) -> Vec<u8> {
        let mut response = OsString::from(if self.status_code == 0 {
            "ack-ok\n"
        } else {
            "error\n"
        });

        let sc_str = OsString::from(self.status_code.to_string());
        // Use newlines to delineate chunks of data
        response.push(sc_str);
        response.push("\n");

        response.push("command\n");
        response.push(&self.cmd);
        response.push("\n");

        response.push("arb-cmd-stdout\n");
        response.push(&self.stdout);
        response.push("\n");

        response.push("arb-cmd-stderr\n");
        response.push(&self.stderr);
        return response.into_encoded_bytes();
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

    loop {
        // Special address 0000 is like INADDR_ANY.
        // The socket needs to get re-created each time
        // so that we can stay bound to 0.0.0.0
        let sock = UdpSocket::bind(format!("0.0.0.0:{listen_port}"))
            .expect("Need to be able to bind socket to given listen port.");
        sock.set_read_timeout(None)
            .expect("Need to be able to set socket timeout");

        let Some((cmd, _)) = receive_command(&sock) else {
            eprintln!("Failed to parse command from UDP packet.");
            continue;
        };
        // If there is a problem executing part of the command,
        // put the error msg into the wrapper stderr
        let res = match execute(&cmd) {
            Ok(r) => r,
            Err(e) => OutputWrapper {
                cmd: OsString::from_vec(cmd),
                stdout: OsString::from(""),
                stderr: OsString::from(&format!("{e:?}")),
                status_code: -1,
            },
        };

        // we're using UDP so it doesn't actually
        // "connect" but this is syntactic sugar
        sock.connect(&send_to_me)
            .expect("Must be able to forward to specified destination address");
        reply_with(&res, &sock);
    }
}

fn reply_with(res: &OutputWrapper, sock: &UdpSocket) {
    /* Reply to the given socket with the results in OutputWrapper.
      the reply format is to split up
      stdout and stderr with a header
      indicating if the command worked or not
    */

    // slice response up into chunks and send it off
    let res_bytes = res.to_packet();
    const STEP: usize = 512;
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("time should go forward")
        .as_secs();
    for i in (0..res_bytes.len()).step_by(STEP) {
        let max_idx = std::cmp::min(res_bytes.len(), i + STEP);

        let mut send_bytes = res_bytes[i..max_idx].to_vec();
        if send_bytes.len() != STEP {
            let padding: usize = STEP - send_bytes.len();
            send_bytes.append(&mut vec![0u8; padding]);
        }
        
        // timestamp
        send_bytes.insert(0, ((ts >> 24) & 0xff) as u8);
        send_bytes.insert(0, ((ts >> 16) & 0xff) as u8);
        send_bytes.insert(0, ((ts >> 8) & 0xff) as u8);
        send_bytes.insert(0, (ts & 0xff) as u8);
        
        let packet_ordering = (i / STEP) as u16;
        send_bytes.push((packet_ordering & 0xff) as u8);
        send_bytes.push(((packet_ordering >> 8) & 0xff) as u8);

        sock.send(&send_bytes).expect("failed to send UDP response");
    }

    // Send a final message saying that data isn't flowing any more
    sock.send("arb-cmd-finished".as_bytes())
        .expect("failed to send end-of-message");
}

fn receive_command(sock: &UdpSocket) -> Option<(Vec<u8>, SocketAddr)> {
    /* Receive a command as a series of bytes from a socket.
      Returns a tuple (cmd, sender address)
    */

    // The command can be up to 8192 bytes long
    // Any longer gets dropped
    let mut buf = [0; 8192];
    let (num_recv, sender) = sock.recv_from(&mut buf).ok()?;

    // Drop empty bytes from the buffer
    let vecta = buf[..num_recv].to_vec();
    return Some((vecta, sender));
}

fn execute(cmd: &Vec<u8>) -> std::io::Result<OutputWrapper> {
    /* Execute a command given as a string as a subprocess
       in a shell.
       The shell is invoked as `bash -l -s` and the
       command is piped to its stdin;
       its stdout and stderr are captured separately.
       In this way, typical shell syntax and nicities
       like loops, redirection, and pipes may be used.
    */

    // Execute the command
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

    return Ok(OutputWrapper::from(&cmd, &out));
}
