Jemena Usage Summary
====================

Simple CLI to summarize electricity usage information downloaded from Jemena.


Usage
-----

```
Usage: jemena.py [OPTIONS] COMMAND [ARGS]...

  Tool for downloading electricity usage data from Jemena.

Options:
  --help  Show this message and exit.

Commands:
  daily    Plot daily usage.
  plot     Plot high frequency data.
  profile  Plot average daily usage profile.
  update   Fetch latest data from Jemena.
```

Set up:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .jemenarc.sample ~/.jemenarc
vi ~/.jemenarc
python3 jemena.py --help
```
