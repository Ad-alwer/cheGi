"""Extract ProductCode from an MSI file."""
import re
import sys

with open(sys.argv[1], "rb") as f:
    data = f.read()

text = data.decode("latin-1")
idx = text.find("ProductCode")

if idx >= 0:
    guids = re.findall(
        r"\{[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\}",
        text[idx : idx + 200],
        re.I,
    )
    if guids:
        print(guids[0])
