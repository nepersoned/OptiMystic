#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash deploy/aws/bootstrap-ec2.sh
#
# Target:
#   Ubuntu 22.04+ EC2

echo "[1/6] apt update"
sudo apt-get update -y

echo "[2/6] install base packages"
sudo apt-get install -y ca-certificates curl git gnupg lsb-release

echo "[3/6] install docker"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$USER"

echo "[4/6] optional: install nvidia container toolkit if NVIDIA GPU exists"
if command -v nvidia-smi >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

  sudo apt-get update -y
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
fi

echo "[5/6] diagnostics"
docker --version
docker compose version
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
fi

echo "[6/6] done"
echo "Re-login (or run: newgrp docker) before running docker commands without sudo."
