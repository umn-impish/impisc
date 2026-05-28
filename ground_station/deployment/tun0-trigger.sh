#!/bin/bash
# Configure the addresses for the SSH VPN on tun0

if [ "$IFACE" = "tun0" ]; then
    ip addr add 10.0.0.1 peer 10.0.0.2/30 dev tun0
    ip link set tun0 up
fi
