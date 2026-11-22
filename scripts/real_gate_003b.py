"""Gate 003B metadata-frozen repeat-run analysis after Gate 003 eligibility failure.

Reuses exactly the same non-adaptive raw-vs-CAR score_monitor pipeline
from the failed-to-enroll 8-subject Gate 003. No hyperparameter changes.
"""
from scripts.choose_cross_subject_runs import read_index
from scripts.choose_run_replicates import choose_repeated_runs
from scripts.real_gate_003 import run


def main():
    report=choose_repeated_runs(read_index(),per_subject=3)
    run(out="results/real_gate_003b",selection=report,gate_label="003B")


if __name__=="__main__":
    main()
