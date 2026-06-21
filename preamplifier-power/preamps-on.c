#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <stddef.h>

int main(int argc, char *argv[]) {
    int mem_fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (mem_fd < 0) {
        perror("Can't open /dev/gpiomem");
        exit(EXIT_FAILURE);
    }

    const auto psize = getpagesize();
    void *gpio_map = mmap(
        NULL,
        psize,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        0
    );

    if (gpio_map == MAP_FAILED) {
        perror("mmap error");
        exit(EXIT_FAILURE);
    }

    volatile uint32_t *gpio = (volatile uint32_t *)gpio_map;

    constexpr auto BYTE_IDX_SCALE = 4;
    constexpr ptrdiff_t GPSET0_OFFSET = 0x1c;
    // Set the preamplifier channels HIGH simultaneously
    gpio[GPSET0_OFFSET / BYTE_IDX_SCALE] = (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7);

    return 0;
}
