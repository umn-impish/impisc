#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <stddef.h>
#include <time.h>

int main(int argc, char *argv[]) {
    long delay = 0;
    if (argc > 1) {
        delay = atol(argv[1]);
    }

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

    constexpr uint32_t BYTE_IDX_SCALE = 4;
    constexpr ptrdiff_t GPSET0_OFFSET = 0x1c;
    struct timespec ts = {.tv_sec = 0, .tv_nsec = delay};
    constexpr uint32_t gpios[] = {4, 5}; //, 6, 7};
    for (size_t i = 0; i < ((sizeof gpios) / 4); ++i) {
	    gpio[GPSET0_OFFSET / BYTE_IDX_SCALE] = (1 << gpios[i]);
	    nanosleep(&ts, NULL);
    }

    return 0;
}
