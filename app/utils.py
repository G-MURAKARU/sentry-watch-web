from datetime import datetime
import random
import copy
from operator import itemgetter
from collections import deque
from collections import Counter


# TIME WILL BE MANIPULATED IN EPOCH TIME - EASIER TO DO MATH (for the check-in timestamps and check-in window)

# variables to store checkpoint IDs
A: str = "Checkpoint A"
B: str = "Checkpoint B"
C: str = "Checkpoint C"
D: str = "Checkpoint D"

# premises adjacency dictionary i.e. mapping each checkpoint and its immediate neighbours
checkpoints = {
    A: [B, D],
    B: [A, C],
    C: [D, B],
    D: [C, A],
}

# path duration dictionary, maps a path to how long it takes to patrol it in seconds
durations = {
    (A, B): 600,
    (B, C): 900,
    (C, D): 1200,
    (D, A): 1500,
}

# route generation algorithm, will loop repeatedly until a valid route is generated
# criteria for a valid route:
# 1. all paths i.e A-B, B-C, C-D and D-A are patrolled
# 2. the difference in frequency of the most patrolled path and the least patrolled path should not exceed 2

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


def generate_route(
    sentries: list[tuple[str]],
    start_date: datetime,
    start_time: datetime,
    shift_dur_hour: int,
    shift_dur_min: int,
):
    # necessary epoch times to evaluate - start of shift and end of shift
    # combines sent date and sent time
    shift_start: int = datetime.timestamp(
        datetime.combine(start_date, start_time)
    )
    shift_dur: int = (shift_dur_hour * 60 * 60) + (shift_dur_min * 60)
    shift_end: int = shift_start + shift_dur

    while True:
        # routes list stores instantaneous check-in information (dictionaries)
        # check-in information format:

        # [{
        #     id: sentry ID to expect
        #     checkpoint: checkpoint at which above sentry is expected
        #     time: time at which the sentry is expected (epoch)
        #     checked: whether the sentry has validly checked in or not
        # },
        # others...]
        # done in the inner loop (marked by timestamps)

        routes: list[dict] = []

        # ind_routes list stores each sentry's route, for record-keeping/reference
        # sentry route format:

        # [{
        #     id: sentry-on-duty ID
        #     route: a list of sentry's route info, i.e.
        #           [{
        #               checkpoint: checkpoint at which particular sentry is expected
        #               time: time at which the sentry is expected
        #            }, others...]
        # },
        # others...]
        # done in the outer loop (marked by IDs)

        ind_routes: list[dict] = []

        # paths list stores each generated patrol path as the full route is generated
        # will be used to count the patrol frequencies for each path

        paths: list[tuple] = []

        for name, card in sentries:
            # routes will be generated one sentry (ID) at a time
            # all sentry shifts should start at the same time i.e. at the beginning of the shift
            current_time: int = shift_start

            # each route will start at a random checkpoint, and check-in info is stored in routes list
            starting_checkpoint: str = random.choice([A, B, C, D])
            id_dict: dict = {
                "id": card,
                "checkpoint": starting_checkpoint,
                "time": current_time,
                "checked": False,
            }

            # individual check-in info is also stored at beginning of shift
            # NB: time here is stored as local date and time (not epoch), derived from epoch time
            route_dict: dict = {
                "name": name,
                "card": card,
                "route": [
                    {
                        "id": card,
                        "checkpoint": starting_checkpoint,
                        "time": current_time,
                        "checked": False,
                    }
                ],
            }

            # check-in info in routes list
            # need to store a copy of the dict - dict is a reference data type
            routes.append(copy.deepcopy(id_dict))

            # second, explained above
            second: str = ""

            while current_time < shift_end:
                first: str = second or starting_checkpoint
                # if second is "", assign to start instead

                # pick second at random from immediate neighbours
                second: str = random.choice(checkpoints[first])

                # pair the two checkpoints to form a path
                path: tuple = (first, second)

                # obtain the duration to patrol that path
                path_duration = durations.get(path)

                # if path is in reverse i.e. (B, A) instead of (A, B), it does not exist in the durations dict
                # the .get() function will return None
                # if it returns None, reverse the path then search the durations dict again

                # if not None == if not False == if True
                if not path_duration:
                    path = tuple(reversed(path))
                    path_duration = durations.get(path)

                # update the current time path to reflect the time offset (time taken to patrol generated path)
                current_time += path_duration

                # create the check-in info dictionary
                id_dict["id"] = card
                id_dict["checkpoint"] = second
                id_dict["time"] = current_time
                id_dict["checked"] = False

                # create a route entry for the current sentry
                route_dict["route"].append(
                    {
                        "id": card,
                        "checkpoint": second,
                        "time": current_time,
                        "checked": False,
                    }
                )

                # copy check-in info dict to routes list
                routes.append(copy.deepcopy(id_dict))

                # add the current path to paths list
                paths.append(path)

            # copy sentry's route info to individual routes (ind_routes) list
            ind_routes.append(copy.deepcopy(route_dict))

        # generates and returns a list of path frequencies from paths list, format: [(path, frequency), ...]
        # e.g. ( ('Chk A', 'Chk B'), 20 ) -> the path from Chk A to Chk B was patrolled 20 times in total
        path_freqs = Counter(paths).most_common()

        # checking the valid path criteria outlined above,
        # if valid then break out of 'while True' loop
        # if not, loop again
        if (
            len(path_freqs) == 4
            and (path_freqs[0][1] - path_freqs[-1][1]) < 3
        ):
            break

    # info for database storage
    return shift_start, shift_end, path_freqs, ind_routes
