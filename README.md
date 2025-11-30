# 📦 Tonutils ADNL CTL

[![TON](https://img.shields.io/badge/TON-grey?logo=TON&logoColor=40AEF0)](https://ton.org)
![Python Versions](https://img.shields.io/badge/Python-3.10%20--%203.14-black?color=FFE873&labelColor=3776AB)
[![PyPI](https://img.shields.io/pypi/v/tonutils-adnlctl.svg?color=FFE873&labelColor=3776AB)](https://pypi.python.org/pypi/tonutils-adnlctl)
[![License](https://img.shields.io/github/license/nessshon/tonutils-adnlctl)](LICENSE)

**Tonutils ADNL CTL** is a minimal CLI utility for inspecting TON lite-server clients.

![Screen](screen.png)

## Installation

```bash
pip install tonutils-adnlctl
```

## Usage

**Mainnet**

```commandline
tonutils-adnlctl status -n mainnet
```

**Testnet**

```commandline
tonutils-adnlctl status -n testnet
```

**From config**

```commandline
tonutils-adnlctl status -n mainnet -c /path/to/config.json
tonutils-adnlctl status -n mainnet -c https://example.com/config.json
```

## License

This repository is distributed under the [MIT License](LICENSE).
