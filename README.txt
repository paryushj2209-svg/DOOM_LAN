FOSS-BU ARENA - LINUX x86-64 PREVIEW

Requirements: a 64-bit x86 Linux desktop, Python 3 with tkinter, the libraries required by the official Zandronum 3.2.1 Linux build, and a graphical session. Ubuntu 24.04 x86-64 is the intended starting point; this package has not yet been tested on Linux.

On Ubuntu 24.04, the following installs the usual direct dependencies (some may already exist):
  sudo apt update
  sudo apt install python3 python3-tk libsdl1.2debian libgtk2.0-0t64 libjpeg8 libglu1-mesa libgl1 libopus0 libssl3t64 libbz2-1.0 zlib1g

Extract the archive, open a terminal in the extracted folder, and run:
  sh start.sh

Choose Classic 1v1 or 1v1 + zombies. Both players must choose the same mode and be on the same Wi-Fi. The host clicks Host match and shares the displayed Wi-Fi IPv4 address. The other player enters the address and clicks Join. Keep the host server open and close it using Stop my server when finished.

The launcher extracts game files to ~/.local/share/FOSS-BU Arena/1.0.0-linux. The package is for x86-64 CPUs, not Raspberry Pi ARM. Windows and Linux packages contain matching game data and Zandronum 3.2.1, but cross-platform multiplayer and zombie behavior remain untested. The earlier game-closing issue remains unresolved.

FreeDM is licensed under a BSD-style license, Zandronum has its own license, and the official engine bundle includes FMOD Ex, a separate proprietary component. See the license and credit files extracted with the game and https://www.fmod.com/legal before public distribution.
