from .bnb import branch_and_bound
from .greedy import list_scheduling, lpt

ALGORITHMS = {
    "ls": list_scheduling,
    "lpt": lpt,
}

__all__ = ["list_scheduling", "lpt", "branch_and_bound", "ALGORITHMS"]
