mod args;
use clap::Parser;

fn main() {
    let args = args::ProgramArgs::parse();

    println!("da port is {}", args.port);
}
