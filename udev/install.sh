#!/bin/sh

mkdir -p /etc/udev/rules.d
curl https://raw.githubusercontent.com/anthroarts/artshow-jockey/main/udev/98-artshow-printers.rules \
    -o /etc/udev/rules.d/98-artshow-printers.rules

mkdir -p /etc/udev/scripts
curl https://raw.githubusercontent.com/anthroarts/artshow-jockey/main/udev/unbind_usblp.sh \
    -o /etc/udev/scripts/unbind_usblp.sh
chmod +x /etc/udev/scripts/unbind_usblp.sh
