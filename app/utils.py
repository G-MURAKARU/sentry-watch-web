import sys
import math
import copy
import random
from collections import Counter
from datetime import datetime

# TIME WILL BE MANIPULATED IN EPOCH TIME - EASIER TO DO MATH (for the check-in timestamps and check-in window)


# check-in window - x seconds before and after the set check-in time within which a scan is considered valid
CHECK_IN_WINDOW = 30


# route generation algorithm, will loop repeatedly until a valid route is generated
# criteria for a valid route:
# 1. all paths i.e A-B, B-C, C-D and D-A are patrolled
# 2. the difference in frequency of the most patrolled path and the least
#     patrolled path should not exceed the sqare root of the path count

# WORKING OF THE ALGORITHM:
# example route:
# (abstract) A-B, B-C, C-D, D-A == [(A, B), (B, C), (C, D), (D, A)] (programmatic) -> [(first, second), ...]
# the second path begins at the end of the first path (the following path begins at the end of the previous path)
# at the beginning, no path is set so the 'second' is blank

# meaning that, if no second checkpoint is set then the shift is yet to begin
# hence the shift begins at 'start' defined above instead of at 'second'
# so, 'first' is assigned to 'start'
# if the shift has began, a second checkpoint must have been set
# hence for the new path, 'first' is assigned to 'second' from the previous path

# the 'second' checkpoint is chosen at random from the list of immediate neighbours of 'first'
# defined in the adjacency dictionary above

# the two checkpoints are paired together, e.g. if 'first' is A and 'second' is B
# they are paired as (A, B) and added to paths
# therefore paths becomes [(A, B),...] and so on

# for the check-in info, the time taken to patrol the path e.g. (A, B)
# is got from the durations dictionary above, and added to the current shift time
# e.g if it takes 600 seconds then current shift time (epoch) + 600
# this means that for path (A, B), a sentry is expected at checkpoint B in the next 600 seconds
# i.e. at current time + 600 seconds
# the destination checkpoint and this derived timestamp are then added to the check-in info dictionary
# along with marking checked as False as the sentry has not had a valid check-in

# the current shift time is then updated to reflect the time offset
# such that timings for subsequent paths use the offset time
# as a reference to derive timestamps, mimicking a continuous shift

# this process is done repeatedly until the current shift time goes beyond the shift end time, with each
# check-in info dictionary stored in the routes list

# after that, the same process is carried out for all sentries-on-duty (all IDs)

# after this, the frequency of occurrence of each path is obtained from the paths list and cross-checked
# to verify that the second valid path criterion is met


def generate_circuit(
    sentries: list[tuple[str, str, str]],
    checkpoints: dict[int, list[tuple]],
    start_date: datetime,
    start_time: datetime,
    shift_dur_hour: int,
    shift_dur_min: int,
):
    """
    generates a random sentry circuit/route
    """

    # Calculating the total possible paths
    req_path_count = sum(len(check_paths) for check_paths in list(checkpoints.values()))

    # necessary epoch times to evaluate - start of shift and end of shift
    # combines sent date and sent time
    shift_start: int = int(datetime.timestamp(datetime.combine(start_date, start_time)))
    shift_dur: int = (shift_dur_hour * 60 * 60) + (shift_dur_min * 60)
    shift_end: int = shift_start + shift_dur

    while True:
        # ind_routes list stores each sentry's route, for record-keeping/reference
        # sentry route format:

        # [{
        #     name: sentry-on-duty name
        #     card: alias of assigned card
        #     id: ID of assigned card
        #     route: a list of sentry's route info, i.e.
        #           [{
        #               id: ID of assigned card
        #               checkpoint: checkpoint at which above sentry is expected
        #               time: time at which the sentry is expected (epoch)
        #               checked: whether the sentry has validly checked in or not
        #            }, others...]
        # },
        # others...]
        # done in the outer loop (marked by IDs)

        # the list of dicts marked by the 'route' key will be used to handle belated check-ins

        ind_routes: list[dict] = []

        # For calculating weights for randomising path to take
        check_weights = {
            checkpath: ([sys.maxsize] * len(checkpoints[checkpath]))
            for checkpath in list(checkpoints.keys())
        }

        # paths list stores each generated patrol path as the full route is generated
        # will be used to count the patrol frequencies for each path

        paths: list[tuple[int, int]] = []

        for name, alias, card in sentries:
            # routes will be generated one sentry (ID) at a time
            # all sentry shifts should start at the same time i.e. at the beginning of the shift
            current_time: int = shift_start

            # each route will start at a random checkpoint, and check-in info is stored in routes list
            starting_checkpoint: int = random.choice(list(checkpoints.keys()))

            # individual check-in info is stored at beginning of shift
            # time stored as epoch time
            route_dict: dict = {
                "name": name,
                "card": alias,
                "id": card,
                "route": [
                    {
                        "id": card,
                        "checkpoint": starting_checkpoint,
                        "time": current_time,
                        "checked": False,
                    }
                ],
            }

            # second, explained above
            second: int = None

            while current_time < shift_end:
                first: int = starting_checkpoint if second is None else second
                # if second is None, assign to start instead

                # pick second at random from immediate neighbours together with the path duration
                pick = random.choices(
                    range(len(checkpoints[first])), weights=check_weights[first], k=1
                )[0]
                check_weights[first][pick] /= 2
                second, path_duration = checkpoints[first][pick]

                # pair the two checkpoints to form a path
                path: tuple[int, int] = (first, second)

                # update the current time path to reflect the time offset (time taken to patrol generated path)
                current_time += path_duration

                # create a route entry for the current sentry
                route_dict["route"].append(
                    {
                        "id": card,
                        "checkpoint": second,
                        "time": current_time,
                        "checked": False,
                    }
                )

                # add the current path to paths list
                paths.append(path)

            # copy sentry's route info to individual routes (ind_routes) list
            ind_routes.append(copy.deepcopy(route_dict))

        # generates and returns a list of path frequencies from paths list in descending order, format: [(path, frequency), ...]
        # e.g. ( ('Chk A', 'Chk B'), 20 ) -> the path from Chk A to Chk B was patrolled 20 times in total
        path_freqs = Counter(paths).most_common()

        # Checking that all paths i.e A-B, B-C, C-D and D-A are patrolled and
        # Confirming the difference in frequency of the most patrolled path and the least
        #  patrolled path should not exceed the sqare root of the path count
        if len(path_freqs) == req_path_count and (
            path_freqs[0][1] - path_freqs[-1][1]
        ) <= math.sqrt(req_path_count):
            break  # if valid then break out of 'while True' loop

    # info for database storage
    return shift_start, shift_end, path_freqs, ind_routes


# TODO: create a function for validating a scan
def update_circuit(circuits: list[dict], scan_info: list):
    """
    updates the circuit on a valid scan by setting the checked flag for a check-in item to True
    makes the green dot appear on the frontend
    """

    found = False
    chk, id, time = scan_info

    for circuit in circuits:
        if id == circuit["id"]:
            for route in circuit["route"]:
                # if scan is valid (right sentry, right checkpoint, right time), return message
                if (
                    id == route["id"]
                    and chk == route["checkpoint"]
                    and time
                    in range(route["time"] - CHECK_IN_WINDOW, route["time"] + (CHECK_IN_WINDOW + 1))
                ):
                    route["checked"] = True
                    found = True
                    break
        if found:
            break
