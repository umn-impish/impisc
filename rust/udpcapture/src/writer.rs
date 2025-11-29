use chrono::prelude::*;
use std::fs::File;
use std::io::{Write, BufWriter};
use std::path::Path;

pub struct FileWriter {
    /* A file-writer struct to be used with
     * the conditional args from UDP capture-like programs
     * */
    base_filename: Option<String>,
    open_time: Option<DateTime<Utc> >,
    lifetime: u16,
    file: Option<BufWriter<File> >,
    max_file_size: Option<u64>,
    filename: String,
    file_inc: u32,
    data_written: usize
}

impl FileWriter {
    pub fn new(base_fn: Option<String>, max_size: Option<u64>, lifetime: u16) -> FileWriter {
        FileWriter {
            base_filename: base_fn,
            lifetime: lifetime,
            open_time: None,
            file: None,
            max_file_size: max_size,
            filename: String::new(),
            file_inc: 0,
            data_written: 0
        }
    }

    #[must_use]
    pub fn maybe_write_data(&mut self, data: &Vec<u8>) -> Option<String> {
        /* Writes the given binary data to a buffered file,
         * should that file exist, and should its lifetime exist.
         *
         * If the file lifetime expires, it is closed.
         * If the file is not open, it is opened with an appropriate name.
         * If the file is open, data is written.
         * If the file hits its size limit, it is closed.
         *
         * Returns:
         *     Option<String>: file name when the file gets closed,
         *                     None when it remains open.
         * */
        if self.base_filename.is_none() {
            // Don't open a file, ever.
            return None;
        }

        // Get ready to write data if we can
        if !data.is_empty() && self.file.is_none() {
            self.open_time = Some(Utc::now());
            self.filename = self.make_file_name();
            self.file = Some(
                BufWriter::new(
                    File::create(&self.filename)
                        .expect("Need to be able to write to given base file location")
            ));
        }

        if let Some(dafile) = &mut self.file {
            dafile.write_all(data)
                  .expect("Data should be writable to a binary file");
            // Manually track how much data we write because calling `stream_position` on
            // a buffered writer causes the buffer to be flushed.
            self.data_written += data.len();
        }

        if self.file_full() || self.expired() {
            // Take the File and drop it (immediate close)
            if let Some(f) = &mut self.file {
                // Unwrap the retval so we panic on error
                f.flush().unwrap();
            }
            drop(self.file.take());
            self.data_written = 0;
            // Clear the open_time so
            // self.expired() behaves correctly
            self.open_time = None;
            return Some(self.filename.clone());
        }
        return None;
    }

    fn make_file_name(&mut self) -> String {
        /* Given the "base" file name stored in the struct,
         * construct a .bin filename for output which contains
         * the date, as well as a repeat number (in case the 
         * same timestamp contains more than one file).
         * */
        let time_str = format!("{}", self.open_time.unwrap().format("%Y-%j-%H-%M-%S"));
        // This loop should hopefully only need one iteration,
        // but if a file of the same name is created by a separate process,
        // we want to not overwrite that one!
        // So, keeping the loop and the Path::exists call is a good idea.
        loop {
            let fn_start = format!(
                "{}_{}",
                &self.base_filename.clone().unwrap(),
                &time_str);

            // If we are creating a file at the same time as a prior one,
            // increment the counter regardless of whether or not the _N
            // version exists
            if (self.filename.len() >= fn_start.len()) && 
               (fn_start == self.filename[..fn_start.len()])
            {
                self.file_inc += 1;
            }
            else {
                self.file_inc = 0;
            }
            let maybe_filename = format!("{}_{}.bin", &fn_start, self.file_inc);
            if !Path::new(&maybe_filename).exists() {
                return maybe_filename;
            }
        }
    }

    fn expired(&self) -> bool {
        /* Check if the current file has been open
         * longer than it should have been.
         * */
        if let Some(ot) = &self.open_time {
            let elapsed = (Utc::now() - ot).num_seconds();
            elapsed >= (self.lifetime as i64)
        } else {
            // File not open; not expired
            false
        }
    }

    fn file_full(&mut self) -> bool {
        self.data_written >= (self.max_file_size.unwrap_or(u64::MAX) as usize)
    }
}
