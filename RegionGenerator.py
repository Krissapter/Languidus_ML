import itertools
import json

def generateRegion():
    with open("RegionDataset.JSON", "w") as f:
        f.write("[\n")
        first = True
        for a0, a1, a2, a3, a7, a8, a9 in itertools.product(
            range(6), range(2), range(2), range(2),
            range(14), range(14), range(14)
        ):
            arr = [
                a0, a1, a2, a3,
                0 if a7 == 0 else 1,
                0 if a8 == 0 else 1,
                0 if a9 == 0 else 1,
                a7, a8, a9
            ]
            if not first:
                f.write(",\n")
            json.dump(arr, f)
            first = False
        f.write("\n]")
generateRegion()