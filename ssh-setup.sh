#!/bin/bash
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGTvMLG2omkEXqMrdGD6oiHiSVUojAgsfbjT97Z0BFze ralph@localhost" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
echo "SSH key installed!"
