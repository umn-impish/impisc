/* 
    A command executor program.

    Accepts an arbitrary command via UDP socket.
    Max length is 1024B long.

    Command is executed using `bash -sl` (see man bash)

    stdout and stderr are captured and sent back separately.
    packets are broken into 1024B chunks, and the 1025th byte
    indicates the packet "sequence number".
*/

use std::ffi::{OsString, OsStr};
// Unix-specific byte string decoding
use std::os::unix::ffi::OsStrExt;
use std::net::{UdpSocket, SocketAddr};
use std::process::{Command, Stdio, Output};
// Impl's needed for writing onto stdio of process
use std::io::{Write};

const PORT: u16 = 35000;

/* OutputWrapper wraps a process result
   into a nice struct. Its stderr field
   can also capture the _shell_ stderr in case
   of some kind of OS error getting thrown before
   or during execution.
 */
struct OutputWrapper {
    stdout: OsString,
    stderr: OsString,
    status_code: i32
}

impl OutputWrapper {
    fn from(proc_out: &Output) -> OutputWrapper {
        return OutputWrapper {
            stdout:      OsStr::from_bytes(&proc_out.stdout).into(),
            stderr:      OsStr::from_bytes(&proc_out.stderr).into(),
            status_code: proc_out.status.code().unwrap_or(0)
        }
    }

    fn to_packet(&self) -> Vec<u8> {
        let mut response = OsString::from(
            if self.status_code == 0 { "ack-ok\n" } else { "error\n" }
        );

        let sc_str = OsString::from(self.status_code.to_string());
        // Use newlines to delineate chunks of data
        response.push(sc_str);
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
    loop {
        // Special address 0000 is like INADDR_ANY.
        // The socket needs to get re-created each time
        // so that we can stay bound to 0.0.0.0
        let sock = UdpSocket::bind(format!("0.0.0.0:{PORT}"))
                            .expect("Couldn't bind socket!");
        sock.set_read_timeout(None).expect("Couldn't set socket timeout");

        let Some((cmd, sender)) = receive_command(&sock)
        else {
            eprintln!("Failed to parse command from UDP packet.");
            continue;
        };
        // If there is a problem executing part of the command,
        // put the error msg into the wrapper stderr
        let res = match execute(&cmd) {
            Ok(r)  => r,
            Err(e) => OutputWrapper{
                stdout: OsString::from(""),
                stderr: OsString::from(&format!("{e:?}")),
                status_code: -1
            }
        };

        // we're using UDP so it doesn't actually 
        // "connect" but this is syntactic sugar
        sock.connect(sender).expect("cannot connect to sender socket");
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
    const STEP: usize = 1024;
    for i in (0..res_bytes.len()).step_by(STEP) {
        let packet_ordering = (i / STEP) as u8;
        let max_idx = std::cmp::min(res_bytes.len(), i+STEP);

        let mut send_bytes = res_bytes[i..max_idx].to_vec();
        if send_bytes.len() != STEP {
            let padding: usize = STEP - send_bytes.len();
            send_bytes.append(&mut vec![0u8; padding]);
        }
        send_bytes.push(packet_ordering);

        sock.send(&send_bytes).expect("failed to send UDP response");
    }

    // Send a final message saying that data isn't flowing any more
    sock.send("finished".as_bytes()).expect("failed to send end-of-message");
}

fn receive_command(sock: &UdpSocket) -> Option<(Vec<u8>, SocketAddr)> {
    /* Receive a command as a series of bytes from a socket.
       Returns a tuple (cmd, sender address)
     */

    // The command can be up to 1024 bytes long
    // Any longer gets dropped
    let mut buf = [0; 1024];
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
                              .stdin( Stdio::piped())
                              .stdout(Stdio::piped())
                              .stderr(Stdio::piped())
                              .spawn()?;
    if let Some(mut stdin) = command.stdin.take() {
        stdin.write_all(cmd)?;
    }

    let out = command.wait_with_output()?;

    return Ok(OutputWrapper::from(&out));
}
