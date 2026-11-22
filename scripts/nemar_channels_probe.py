"""Read the published BIDS sidecar for a single high-rate NEMAR EDF.

No samples downloaded. Never guess which EEG### label means microphone.
"""
import urllib.request,csv,io,json
from pathlib import Path

BASE="https://data.nemar.org/on007808/v1.0.0/sub-01/ses-20230829/eeg/"
NAME="sub-01_ses-20230829_task-speechopen_acq-pangolin_run-01_channels.tsv"
URL=BASE+NAME


def main():
    with urllib.request.urlopen(URL,timeout=40) as r:
        data=r.read(512000).decode("utf-8-sig")
    rows=list(csv.DictReader(io.StringIO(data),delimiter="\t"))
    special=[row for row in rows if row.get("type","").upper() not in ("EEG","SEEG","ECOG")]
    out={"url":URL,"total_rows":len(rows),
         "column_names":list(rows[0]) if rows else [],
         "first_rows":rows[:3],
         "non_eeg_rows":special,
         "last_16_rows":rows[-16:],
         "warning":"Public metadata only: no signal data and no inferred hardware path."}
    p=Path("results/nemar_channels_probe.json");p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2)[:14000],flush=True)


if __name__=="__main__":
    main()
