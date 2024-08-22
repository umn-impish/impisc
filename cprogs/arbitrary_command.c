/*
Accept an arbitrary command from a UDP packet
and run it in a shell using popen

To compile:
gcc arbitrary_command.c -std=gnu17 -o arbc -Wall -Werror -Wpedantic

You can test it in Python:
	import socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.sendto(b'head -n10 /dev/urandom', ('localhost', 35000)
	print(s.recvfrom(2048))
*/
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/socket.h>
#include <netinet/in.h>

// stole from Python
const unsigned short EXEC_PORT = 35000;
struct Response {
    char msg[1024];
    uint8_t seq_num;
};

void listen_loop(int socket);

int main(int argc, char *argv[]) {
    int sock_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_fd < 0) {
        fprintf(stderr, "Socket failed to allocate: %s\n", strerror(errno));
        return -1;
    }

    struct sockaddr_in sai;
    memset(&sai, 0, sizeof(sai));
    sai.sin_family = AF_INET;
    sai.sin_port = htons(EXEC_PORT);
    sai.sin_addr.s_addr = INADDR_ANY;

    int rc = bind(sock_fd, (struct sockaddr*)&sai, sizeof(sai));
    if (rc < 0) {
        fprintf(stderr, "Failed to bind socket: %s\n", strerror(errno));
        return -1;
    }

    listen_loop(sock_fd);

    return 0;
}

void listen_loop(int sock_fd) {
    #define BUF_SZ 1024
    char cmd_buf[BUF_SZ];
    char ret_buf[BUF_SZ];

    struct sockaddr_in sender;
    memset(&sender, 0, sizeof(sender));
    while (true) {
        // Clear buffers at start of each iteration
        memset(cmd_buf, 0, BUF_SZ);
        memset(ret_buf, 0, BUF_SZ);

        socklen_t sz = sizeof(sender);
        ssize_t rc = recvfrom(
            sock_fd, cmd_buf, BUF_SZ,
            0, (struct sockaddr*)&sender, &sz);

        if (strncmp(cmd_buf, "KILLIT", 6) == 0) {
            // special death string heheh
            exit(0);
        }

        if (rc < 0) {
            fprintf(stderr, "Error receiving: %s\n", strerror(errno));
            exit(1);
        }

        // Safely null-terminate the command
        cmd_buf[BUF_SZ-1] = '\0';
        // execute it (pipe the process output back to us)
        FILE *pipe = popen(cmd_buf, "r");
        if (pipe == NULL) {
            fprintf(stderr, "Error opening pipe: %s\n", strerror(errno));
            exit(1);
        }

        uint8_t seq_num = 0;
        // keep reading until the stream is empty
        while (!feof(pipe)) {
            // Read at most BUF_SZ
            (void) fread(ret_buf, 1, BUF_SZ, pipe);
            if (ferror(pipe)) {
                fprintf(stderr, "Error reading from pipe: %s\n", strerror(errno));
                exit(1);
            }

            // pack up the received data
            struct Response res;
            // ordering of the packets
            res.seq_num = seq_num++;
            memcpy(res.msg, ret_buf, BUF_SZ);

            // send the response to our friend
            sendto(sock_fd, &res, sizeof(res), 0, (struct sockaddr*)&sender, sizeof(sender));
        }

        // Close da process when we're done so we don't leak memory
        pclose(pipe);
    }
}
