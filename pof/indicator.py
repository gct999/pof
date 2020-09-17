"""
    Filename: indicator.py
    Description: Contains the code for implementing an indicator class
    Author: Gavin Treseder | gct999@gmail.com | gtreseder@kpmg.com.au | gavin.treseder@essentialenergy.com.au
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Dict
import collections

import numpy as np
import scipy.stats as ss
from matplotlib import pyplot as plt

if __package__ is None or __package__ == "":
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pof.load import Load
from pof.helper import str_to_dict
from pof.config import indicator_config as cf

# TODO overload methods to avoid if statements and improve speed
# TODO make sure everything works for conditions in both direction
# TODO robust testing
# TODO move threshold down into condition indciator so indicator is purely bool


@dataclass
class Indicator(Load):

    """

    Methods

        from_dict()

        load_asset_data()

        sim_timeline()

        sim_failure_timeline()

    """

    name: str = "indicator"
    pf_curve: str = None
    pf_interval: int = None
    pf_std: int = 0
    perfect: bool = None
    failed: bool = None
    decreasing: bool = field(init=False)

    threshold_detection: int = None
    threshold_failure: int = None

    _profile: Dict = field(init=False)
    _timeline: Dict = field(init=False)
    _timelines: Dict = field(init=False)

    def __post_init__(self):

        self.set_limits(perfect=self.perfect, failed=self.failed)
        self.set_threshold(
            detection=self.threshold_detection, failure=self.threshold_failure
        )
        self.set_pf_curve(pf_curve=self.pf_curve)
        self.set_pf_interval(pf_interval=self.pf_interval)
        self.reset()

    def sim_indicator_timeline(self):

        # Overloaded
        NotImplemented

    def sim_failure_timeline(self):

        # Overloaded
        NotImplemented

    def restore(self):

        NotImplemented

    def reset(self):

        self._profile = dict()
        self._timeline = dict()
        self._timelines = dict()

    def set_pf_curve(self, pf_curve):

        if pf_curve in cf.PF_CURVES:
            self.pf_curve = pf_curve
        else:
            if cf.USE_DEFAULT:
                self.pf_curve = cf.PF_CURVES
            else:
                raise ValueError("pf_curve must be from: %s" % (cf.PF_CURVES))

    def set_pf_interval(self, pf_interval=None):

        # TODO add robust testing around pf_interval non negative numbers etc
        if pf_interval is None:
            if self.pf_interval is None:
                if cf.USE_DEFAULT:
                    print(
                        "%s - %s - pf_interval set to DEFAULT %s"
                        % (self.__class__.__name__, self.name, cf.PF_INTERVAL)
                    )
                    self.pf_interval = cf.PF_INTERVAL
                else:
                    raise ValueError(
                        "%s - %s - pf_interval required"
                        % (self.__class__.__name__, self.name)
                    )
        else:
            self.pf_interval = pf_interval

    def set_limits(self, perfect=None, failed=None):
        # TODO Add test make sure these tests work for bool and int

        if perfect is None:
            if self.perfect is None:
                if cf.USE_DEFAULT:
                    self.perfect = cf.PERFECT
                else:
                    raise ValueError(
                        "%s - %s - perfect value required"
                        % (self.__class__.__name__, self.name)
                    )
        else:
            self.perfect = perfect

        if failed is None:
            if self.failed is None:
                if cf.USE_DEFAULT:
                    self.failed = cf.FAILED
                else:
                    raise ValueError(
                        "%s - %s - failed value required"
                        % (self.__class__.__name__, self.name)
                    )
        else:
            self.perfect = perfect

        # Set perfect
        if self.perfect > self.failed:
            self.decreasing = True
        else:
            self.decreasing = False

        self.upper = abs(self.perfect - self.failed)

    def set_threshold(self, detection=None, failure=None):
        if detection is None:
            if self.threshold_detection is None:
                self.threshold_detection = self.perfect
            else:
                self.threshold_detection = detection

        if failure is None:
            if self.threshold_failure is None:
                self.threshold_failure = self.failed
            else:
                self.threshold_failure = failure

    # ****************** Get methods **************

    def agg_timeline(self):

        if self.decreasing:
            timeline = self.perfect - (
                self.perfect - np.array(list(self._timeline.values()))
            ).sum(axis=0)
            timeline[timeline < self.failed] = self.failed
        else:
            timeline = self.perfect + (
                np.array(list(self._timeline.values())) - self.perfect
            ).sum(axis=0)
            timeline[timeline > self.failed] = self.failed
        return timeline

    def get_timeline(self, name=None):
        """ Returns the timeline for a name if it is in the key or if no key is passed and None is not a key, it aggregates all timelines"""
        try:
            timeline = self._timeline[name]
        except KeyError as name_not_in_timeline:
            if name is None:
                timeline = self.agg_timeline()
            else:
                raise KeyError from name_not_in_timeline(
                    "Name - %s - is not in %s %s timeline"
                    % (name, self.__class__.__name__, self.name)
                )

        return timeline

    #  ********************* Interface methods ***********************

    def plot_profile(self):

        for name, profile in self._profile.items():
            plt.plot(profile, label=name)

        plt.title("Indicator Profile")
        plt.show()

    def plot_timeline(self):

        for name, timeline in self._timeline.items():
            # Plot with matplotlib
            plt.plot(timeline, label=name)

        plt.title("Indicator Timeline")
        plt.show()

    def plot_timelines(self, i=None, n=None):

        if i is not None:
            if n is None:
                self._plot_timeline(self._timelines[i])
            else:
                for idx in range(i, n):
                    plt.plot(self._timeline[idx])

        plt.show()

    def _plot_timeline(self, _timeline=None):
        if _timeline is None:
            _timeline = self._timeline

        for cause, timeline in _timeline.items():
            plt.plot(timeline)
            # plt.plot(self.t_condition, self.current(), "rd")

    def update(self, id_object, value=None):
        """"""
        if isinstance(id_object, str):
            self.update_from_str(id_object, value, sep="-")

        elif isinstance(id_object, dict):
            self.update_from_dict(id_object)

        else:
            print(
                'ERROR: Cannot update "%s" from string or dict'
                % (self.__class__.__name__)
            )

    def update_from_str(self, id_str, value, sep="-"):

        id_str = id_str.split(self.name + sep, 1)[1]

        dict_data = str_to_dict(id_str, value, sep)

        self.update_from_dict(dict_data)

    def update_from_dict(self, dict_data):

        for key, value in dict_data.items():

            if key in ["name"]:
                self.__dict__[key] = value
            elif key in ["parent"]:
                self.component = value
            else:
                raise KeyError(
                    'ERROR: Cannot update "%s" from dict with key %s'
                    % (self.__class__.__name__, key)
                )


@dataclass
class ConditionIndicator(Indicator):

    name: str = "ConditionIndicator"

    def __post_init__(self):
        super().__post_init__()

        self.pf_curve_params = NotImplemented  # TODO for complex condition types

        # Current accumulation
        self._accumulated = dict()

    # ********************** Timeline methods ******************************

    def sim_timeline(
        self, t_stop=None, t_start=0, pf_interval=None, pf_std=None, name=None
    ):
        """
        Returns the timeline that considers all the accumulated degradation
        """

        # Use the condition parameters if unique parameters aren't provided TODO maybe remove
        if pf_interval is None:
            pf_interval = self.pf_interval

        if pf_std is None:
            pf_std = self.pf_std

        # Adjust the pf_interval based on the expected variance in pf_std
        if pf_std is not None:
            pf_interval = int(pf_interval + ss.norm.rvs(loc=0, scale=pf_std))

        # Set the condition profile if it hasn't been created already or if uncertainty is needed
        if pf_interval not in self._profile:
            self._set_profile(pf_interval=pf_interval, name=name)

        # Get the timeline
        self._timeline[name] = self._acc_timeline(
            t_start=t_start, t_stop=t_stop, pf_interval=pf_interval, name=name
        )

        return self._timeline[name]

    def _set_profile(
        self, perfect=None, failed=None, pf_interval=None, pf_std=None, name=None
    ):

        # TODO Illyse - add the other profile types
        # TODO maybe make this work using pf_interval and name so that it doesn't do as much recalcuting
        """
        Linear: μ(t) = b + a × t
        Exponential: μ(t) = b × exp(a × t)
        Power: μ(t) = b × t a
        Logarithm: μ(t) = a × ln(t) + b
        Lloyd-Lipow: μ(t) = a − (b/t)
        """

        # Use the condition parameters if unique parameters aren't provided TODO maybe remove/
        if perfect is None:
            perfect = self.perfect

        if failed is None:
            failed = self.failed

        if pf_interval is None:
            pf_interval = self.pf_interval

        if pf_std is None:
            pf_std = self.pf_std

        # Get the time to be investitaged
        x = np.linspace(0, pf_interval, pf_interval + 1)

        if self.pf_curve == "linear":

            m = (failed - perfect) / pf_interval
            b = perfect
            y = m * x + b

        elif self.pf_curve == "step":
            y = np.full(self.pf_interval, self.perfect)

        elif self.pf_curve == "exponential" or self.pf_curve == "exp":
            NotImplemented

        self._profile[pf_interval] = y

    def _acc_timeline(self, t_start=0, t_stop=None, pf_interval=None, name=None):
        # TODO this probably needs a delay?
        """
        Returns the timeli
        """

        # Validate times
        t_max = len(self._profile[pf_interval]) - 1
        if t_stop == None:
            t_stop = t_max

        if t_start > t_stop:
            t_start = t_stop

        if t_stop < 0:
            t_start = t_start - t_stop
            t_stop = 0

        profile = self._profile[pf_interval][
            max(0, min(t_start, t_max)) : min(t_stop, t_max) + 1
        ]

        # Adjust for the accumulated condition
        accumulated = self.get_accumulated(name=name)
        if accumulated > 0:
            profile = profile - accumulated
            profile[profile < self.failed] = self.failed

        # Fill the start with the current condtiion
        if t_start < 0:
            profile = np.append(np.full(t_start * -1, profile[0]), profile)

        # Fill the end with the failed condition
        n_after_failure = t_stop - t_start - len(profile) + 1
        if n_after_failure > 0:
            profile = np.append(profile, np.full(max(0, n_after_failure), self.failed))

        return profile

    def sim_failure_timeline(
        self, t_stop=None, t_start=0, pf_interval=None, pf_std=None, name=None
    ):  # TODO this probably needs a delay? and can combine with condtion profile to make it simpler
        """
        Return a sample failure schedule for the condition
        """

        profile = self.sim_timeline(
            t_stop=t_stop,
            t_start=t_start,
            pf_interval=pf_interval,
            pf_std=pf_std,
            name=name,
        )

        if self.decreasing == True:
            tl_f = profile <= self.threshold_failure
        else:
            tl_f = profile >= self.threshold_failure

        return tl_f

    def restore(self):

        NotImplemented

    # ************** Simulate Condition ***************

    def sim(self, t, name=None):
        """
        Return the condition at time t
        """
        self.sim_timeline(t_stop=t, name=name)

        return self._timeline[name][t]

    # ********************* Get Methods **********************

    def get_condition(self):
        if self.decreasing:
            return self.perfect - self.get_accumulated()
        else:
            return self.perfect + self.get_accumulated()

    def get_timeline(self, name=None):
        return self._timeline[name]

    def get_accumulated(self, name=None):  # TODO make this work for arrays of names

        if name is None:
            # Get all the total acumulated condition
            accumulated = sum(self._accumulated.values())

        else:

            # Get the accumulated condition for a single name
            if isinstance(name, str):
                accumulated = self._accumulated.get(name, 0) + self._accumulated.get(
                    "permanent", 0
                )

            # Get the accumulated condition for a list of names
            elif isinstance(name, collections.Iterable):
                accumulated = sum(
                    [self._accumulated.get(key, 0) for key in name]
                ) + self._accumulated.get("permanent", 0)
            else:
                raise TypeError("name should be a string or iterable")

        return accumulated

    # ********************* Set Methods **********************

    def _set_accumulated(self, accumulated, name=None):

        # check accumulated will not exceed the maximum allowable condition
        current = self.get_accumulated()

        self._accumulated[name] = min(
            accumulated, abs(self.perfect - self.failed) - current - accumulated
        )

    def set_condition(self, condition, name=None):
        # TODO consider impact of other impacts

        if self.decreasing:
            self._accumulated[name] = min(
                max(0, self.perfect - condition), self.perfect - self.failed
            )
        else:
            self._accumulated[name] = min(
                max(0, condition - self.perfect), self.failed - self.perfect
            )

    def reset(self):

        super().reset()
        self._reset_accumulated()

    def reset_any(self, target=0, method="reset", axis="time", permanent=False):
        """
        # TODO make this work for all the renewal processes (as-bad-as-old, as-good-as-new, better-than-old, grp)
        """

        # Error with time reset, different method required.

        if method == "reduction_factor":
            accumulated = (abs(self.perfect - self.get_accumulated())) * (1 - target)

        elif method == "reverse":

            accumulated = self.get_accumulated() - target

        elif method == "set":
            accumulated = target

        # Calculate the accumulated condition TODO not working
        if axis == "time":

            NotImplemented

        elif axis == "condition":

            if self.decreasing:
                accumulated = min(max(self.failed, accumulated), self.perfect)
            else:
                accumulated = max(min(self.failed, accumulated), self.perfect)

            self._reset_accumulated(accumulated, permanent=permanent)

    def _reset_accumulated(self, accumulated=0, name=None, permanent=False):

        # Maintain permanent condition loss if set
        if permanent:
            existing_permanent = self._accumulated.get("permanent", 0)
            accumulated = permanent + existing_permanent
            name = "permanent"

        self._accumulated = dict()
        self._set_accumulated(name=name, accumulated=accumulated)

    def update_from_dict2(self, keys):

        try:
            super().update_from_dict(keys)

        except KeyError:
            # Check for condition specific ones
            for key, value in keys.items():
                if key in [
                    "pf_curve",
                    "pf_interval",
                    "pf_std",
                    "perfect",
                    "failed",
                    "decreasing",
                    "threshold_protection",
                    "threshold_failure",
                ]:
                    self.__dict__[key] = value
                else:
                    raise KeyError(
                        'ERROR: Cannot update "%s" from dict with key %s'
                        % (self.__class__.__name__, key)
                    )

    def update_from_dict(self, keys):

        for key, value in keys.items():

            try:
                super().update_from_dict({key: value})
            except KeyError:
                if (
                    False
                ):  # TODO Illyse - the false is just to make the code run, not the acutally condition
                    # is object then update
                    # is it a dict
                    self.__dict__[key] = value
                else:
                    # Check for condition specific ones
                    raise KeyError(
                        'ERROR: Cannot update "%s" - %s from dict with key %s'
                        % (self.__class__.__name__, self.name, key)
                    )


@dataclass
class PoleSafetyFactor(Indicator):

    failed: int = 1
    decreasing: int = True

    def __post_init__(self):
        super().__post_init__()

    def sim_failure_timeline(self):
        """
        Determine if the indicator hsa failed
        """
        # Get the timeline
        timeline = self.safety_factor()

        # Check
        if self.decreasing == True:
            timeline = timeline <= self.threshold_failure
        else:
            timeline = timeline >= self.threshold_failure

        return timeline

    def safety_factor(self, method="simple"):

        if method == "simple":
            sf = self._safety_factor(
                agd=self.component.indicator["external_diameter"].perfect,
                czd=self.component.indicator["external_diameter"].get_timeline(),
                wt=self.component.indicator["wall_thickness"].get_timeline(),
                margin=4,
            )

        elif method == "actual":
            sf = self._safety_factor(
                agd=self.component.conditions["external_diameter"].perfect,
                czd=self.component.conditions["external_diameter"],
                wt=self.component.conditions["wall_thickness"],
                pole_load=self.component.info["pole_load"],
                pole_strength=self.component.info["pole_strength"],
            )

        return sf

    def _safety_factor(
        self, agd, czd, wt, pole_strength=None, pole_load=None, margin=4
    ):
        """
        Calculates the safety factor using a margin of 4 if the pole load and pole strength are not available

            Params:
                agd:    above ground diamater

                czd:    critical zone diameter

                wt:     wall thickness

                margin: the safety margin used when designing the pole

        """

        if pole_load is not None and pole_strength is not None:

            margin = pole_strength / pole_load

        sf = margin * (czd ** 4 - (czd - 2 * wt) ** 4) / (agd ** 3 * czd)

        return sf

    def update_from_dict(self, keys):

        try:
            super().update_from_dict(keys)
        except KeyError:
            # Check for condition specific ones
            for key, value in keys.items():
                if key in ["component", "decreasing"]:
                    self.__dict__[key] = value
                elif key in ["failure"]:
                    self.threshold_failure = value
                else:
                    raise KeyError(
                        'ERROR: Cannot update "%s" from dict with key %s'
                        % (self.__class__.__name__, keys)
                    )


"""
ConditionIndicator
SafetyFactorIndicator

"""

if __name__ == "__main__":
    indicator = Indicator()
    print("Indicator - Ok")
