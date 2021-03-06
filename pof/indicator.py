"""
    Filename: indicator.py
    Description: Contains the code for implementing an indicator class
    Author: Gavin Treseder | gct999@gmail.com | gtreseder@kpmg.com.au | gavin.treseder@essentialenergy.com.au
"""

import collections
import copy
import logging
from typing import List

import numpy as np
import pandas as pd
import scipy.stats as ss
from matplotlib import pyplot as plt

if __package__ is None or __package__ == "":
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pof.decorators import check_arg_positive, coerce_arg_type
from pof.pof_base import PofBase
from pof.helper import str_to_dict
from config import config
import pof.demo as demo

cf = config["Indicator"]


# TODO move timeline to indicator
# TODO overload methods to avoid if statements and improve speed
# TODO make sure everything works for conditions in both direction
# TODO robust testing
# TODO move threshold down into condition indciator so indicator is purely bool
# TODO safety factor has been calculated from aggregated condtion, but condition is reporting condition not condition loss
# TODO check why safety factor is saved as an int not a float
# TODO check safety factor record in timelines
# TODO check boolean of trigger and/or and modification vs. replacement
# TODO check trigger for failure (sf could be 0 for 2 years before registering as a failure)


# TODO make sure pf_interval can only be positive


class PfCurve:
    """
    Descriptor for PF Curve
    """

    # def __init__(self, valid_pf_curves=None):
    #     self.valid_pf_curves = valid_pf_curves

    def __get__(self, obj):
        self.value

    def __set__(self, obj, value):
        if value in self.valid_pf_curves:
            self.value = value
        else:
            raise ValueError("pf_curve must be from: %s" % (self.valid_pf_curves))


class Indicator(PofBase):

    """

    The indicator class is framed so that False is the ideal state and everything is changed from there

    Methods

        from_dict()

        load_asset_data()

        sim_timeline()

        sim_failure_timeline()

    """

    # Class Variables
    PF_CURVES = ["linear", "step"]
    TIME_VARIABLES = ["pf_interval", "pf_std"]
    POF_VARIABLES = []

    def __init__(
        self,
        name: str = "indicator",
        pf_curve: str = "step",
        pf_interval: int = 0,
        pf_std: int = 0,
        perfect: bool = False,
        failed: bool = True,
        threshold_detection: int = None,
        threshold_failure: int = None,
        initial: int = None,
        *args,
        **kwargs,
    ):

        super().__init__(name=name, *args, **kwargs)

        self.pf_curve = pf_curve
        self.pf_interval = pf_interval
        self.pf_std = pf_std

        self.perfect = perfect
        self.failed = failed
        self.decreasing = None

        self.threshold_detection = threshold_detection
        self.threshold_failure = threshold_failure
        self.initial = initial

        self.set_limits()
        self.set_threshold(
            detection=self.threshold_detection, failure=self.threshold_failure
        )

        self._profile = dict()  # TODO del
        self._timeline: dict()
        self._timelines: dict()
        self.reset()

    @classmethod
    def factory(cls, pf_curve=None, indicator_type=None, **kwargs):

        if indicator_type == "ConditionIndicator":
            ind_class = ConditionIndicator

        elif indicator_type == "PoleSafetyFactor":
            ind_class = PoleSafetyFactor

        elif pf_curve in ["linear", "step"]:
            ind_class = ConditionIndicator

        elif pf_curve in ["ssf_calc", "dsf_calc"]:
            ind_class = PoleSafetyFactor

        elif pf_curve is None and indicator_type is None:
            ind_class = Indicator

        else:
            raise ValueError("Invalid Indicator Type")

        return ind_class

    @classmethod
    def from_dict(cls, details=None):
        """
        Overloaded factory for creating indicators
        """
        if isinstance(details, dict):
            pf_curve = details.get("pf_curve", None)
            ind_type = details.get("indicator_type", None)
            ind_class = cls.factory(pf_curve=pf_curve, indicator_type=ind_type)
            ind = ind_class(**details)

        else:
            raise TypeError("Dictionary expected")

        return ind

    def sim_timeline(self, *args):
        logging.debug("Non overloaded function called")
        NotImplemented

    def sim_failure_timeline(self, *args, **kwargs):
        logging.debug("Non overloaded function called")
        NotImplemented

    def restore(self, *args, **kwargs):
        logging.debug("Non overloaded function called")
        NotImplemented

    def reset_any(self, *args, **kwargs):
        logging.debug("Non overloaded function called")
        NotImplemented

    def reset(self, cause=NotImplemented):

        self._timeline = dict()
        self._timelines = dict()

    def reset_for_next_sim(self):
        NotImplemented

    def reset_to_perfect(self):
        NotImplemented

    @property
    def pf_curve(self):
        return self._pf_curve

    @pf_curve.setter
    def pf_curve(self, value):
        if value in self.PF_CURVES:
            self._pf_curve = value
        else:
            raise ValueError("pf_curve must be from: %s" % (self.PF_CURVES))

    @property
    def pf_interval(self):
        return self._pf_interval

    @pf_interval.setter
    # @check_arg_positive("value")
    def pf_interval(self, value: float):
        self._pf_interval = value

    @property
    def perfect(self):
        return self._perfect

    @perfect.setter
    @coerce_arg_type
    def perfect(self, value: float):
        self._perfect = value
        self.set_limits()

    @property
    def failed(self):
        return self._failed

    @failed.setter
    @coerce_arg_type
    def failed(self, value: float):
        self._failed = value
        self.set_limits()

    def set_limits(self, perfect=None, failed=None):
        # TODO Add test make sure these tests work for bool and int

        if perfect is not None:
            self.perfect = perfect

        if failed is not None:
            self.failed = failed

        # Set perfect
        if hasattr(self, "_perfect") and hasattr(self, "_failed"):
            if self._perfect > self._failed:
                self.decreasing = True
            else:
                self.decreasing = False

            self.max_loss = abs(self._perfect - self._failed)

    @property
    def initial(self):
        return self._initial

    @initial.setter
    def initial(self, value=None):
        """ Set the intial """
        # TODO add checks to make sure it is a valid value

        if value is None:
            self._initial = self._perfect
        else:
            self._initial = value

        self.reset_for_next_sim()  # TODO combine set and reset

    def set_threshold(self, detection=None, failure=None):
        if detection is None:
            if self.threshold_detection is None:
                self.threshold_detection = self._perfect
            else:
                self.threshold_detection = detection

        if failure is None:
            if self.threshold_failure is None:
                self.threshold_failure = self._failed
            else:
                self.threshold_failure = failure

    # ****************** Get methods **************

    # TODO split out into conditionIndicator and simplify this method for Indicator to make it faster

    def agg_timeline(self):

        if self.decreasing:
            timeline = self._perfect - (
                self._perfect - np.array(list(self._timeline.values()))
            ).sum(axis=0)
            timeline[timeline < self._failed] = self._failed
        else:
            timeline = self._perfect + (
                np.array(list(self._timeline.values())) - self._perfect
            ).sum(axis=0)
            timeline[timeline > self._failed] = self._failed
        return timeline

    def agg_timelines(self):
        """
        Takes a dictionary of timelines and returns the aggregated timelines
        """
        agg_timeline = []
        for timeline in self._timelines.values():
            if self.decreasing:
                etl = self._perfect - (
                    self._perfect - np.array(list(timeline.values()))
                ).sum(axis=0)
                etl[etl < self._failed] = self._failed
            else:
                etl = self._perfect + (
                    np.array(list(timeline.values())) - self._perfect
                ).sum(axis=0)
                etl[etl > self._failed] = self._failed

            agg_timeline.append(etl)

        return np.stack(agg_timeline)

    def get_timeline(self, name=None):
        # maybe add t_start?
        """ Returns the timeline for a name if it is in the key or if no key is passed and None is not a key, it aggregates all timelines"""
        if name in self._timeline:
            timeline = self._timeline[name]
        elif name is None:
            timeline = self.agg_timeline()
        else:
            raise KeyError(
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

    """def expected_condition(self, conf=0.5):
        ec = self.get_timeline()
        return self._expected_condition(ec, conf)"""

    def _expected_condition(self, ec, conf):
        """
        Returns the expected condition based
        """
        # TODO make work for all condition levels loss:bool=False

        mean = ec.mean(axis=0)
        sigma = ec.std(axis=0)

        # Create a dataframe with mean & sigma
        df_mean_sigma = pd.DataFrame(
            data={"mean": mean, "sigma": sigma},
            columns=["mean", "sigma"],
        )

        # Filter out rows when sigma = 0
        mean_filtered = df_mean_sigma[df_mean_sigma["sigma"] != 0]["mean"]
        sigma_filtered = df_mean_sigma[df_mean_sigma["sigma"] != 0]["sigma"]

        # TODO maybe add np.sqr(len(ec)) to make it stderr

        # Calculate bounds
        df_mean_sigma.loc[df_mean_sigma["sigma"] != 0, "upper"] = ss.norm.ppf(
            (1 - (1 - conf) / 2), loc=mean_filtered, scale=sigma_filtered
        )
        df_mean_sigma.loc[df_mean_sigma["sigma"] != 0, "lower"] = ss.norm.ppf(
            ((1 - conf) / 2), loc=mean_filtered, scale=sigma_filtered
        )

        # Adjust upper and lower to the mean if there is not variance (sigma was 0)
        df_mean_sigma.loc[df_mean_sigma["sigma"] == 0, "upper"] = df_mean_sigma["mean"]
        df_mean_sigma.loc[df_mean_sigma["sigma"] == 0, "lower"] = df_mean_sigma["mean"]

        upper = df_mean_sigma["upper"]
        lower = df_mean_sigma["lower"]

        if self.decreasing:
            upper[upper > self._perfect] = self._perfect
            lower[lower < self._failed] = self._failed
        else:
            upper[upper > self._failed] = self._failed
            lower[lower < self._perfect] = self._perfect

        expected = dict(
            lower=lower,
            mean=mean,
            upper=upper,
        )

        return expected

    def save_timeline(self, idx=None):
        self._timelines[idx] = copy.deepcopy(self._timeline)

    def is_failed(
        self, t_start: int = None, t_end: int = None, cause: str = None
    ) -> List:
        """
        Determines if an indicator has failed between a time range from a cause

        Args:
            t_start: Optional; The time to start checking the failure
            t_end: Optional; The time to stop checking the failure
            cause: Optional; Consider the failure based on the impact of this cause only

        Returns:
            A list of boolean
        """

        timeline = self.get_timeline(cause)[t_start]

        # Check for failure
        if self.decreasing == True:
            failed = timeline <= self.threshold_failure
        else:
            failed = timeline >= self.threshold_failure

        return failed


# TODO exeriment only
class CondIndicator:

    """

    The condition indicator is structured around a concept of condition loss

    Three causes are added during simulations:
        'permanent' - condition loss which cannot be repaired

    Args:
        perfect: the condition at perfect health
        failed: the worst condition possible
        initial: the condition at the start of the simulation


    """

    def sim_timeline(
        self,
        t_start: int,
        t_end: int,
        t_init: int = None,
        pf_interval: int = None,
        pf_std: int = None,
        cause: str = None,
    ) -> List:
        """Gets the existing timeline and updates it so that the condition at t_start is propogated until t_init

        Args:
            t_start: the time the simulation starts
            t_end: the time the simulation ends
            t_init: the time condition loss starts

        Returns:
            A list of conditions over the time period
        """

        # initation occurs at t_start is no t_init is provided
        if t_init is None:
            t_init = t_start

        # Create timeline if it doesn't exist #TODO delete this and make sure timeline always dict
        length = t_end - t_start + 1
        if self._timeline is None:
            self._timeline = {
                "initial": np.full(length, self._initial),
                "permanent": np.full(length, self._permanent),
            }

        # if cause not in self._timeline:
        #     self._timeline[cause] = np.full(length, 0)

        timeline = self.get_timeline(cause)
        profile = self._sim_profile(pf_interval=pf_interval, pf_std=pf_std)

        t_failed = t_init + len(profile)

        # Update the timeline
        timeline[t_start:t_init] = timeline[t_start]
        timeline[t_init:t_end] = profile[t_end - t_init]
        timeline[t_failed:] = timeline[t_failed]

        self._timeline[cause] = timeline

        return timeline

    def _sim_profile(self, pf_interval=None, pf_std=None):
        """
        Simulates a condition profile based on the pf_interval and its uncertainity

        Args:
            pf_interval
            pf_std

        """

        # Use the condition parameters if unique parameters aren't provided TODO maybe remove
        if pf_interval is None:
            pf_interval = self._pf_interval

        if pf_std is None:
            pf_std = self.pf_std

        # Adjust the pf_interval based on the expected variance in pf_std
        if pf_std is not None and pf_std != 0:
            pf_interval = int(pf_interval + round(ss.norm.rvs(loc=0, scale=pf_std)))

        profile = self._calc_profile(pf_interval)

        return profile

    def _calc_profile(self, pf_interval=None):

        # TODO add the other profile types
        # TODO add functools lru cache
        """
        Linear: μ(t) = b + a × t
        Exponential: μ(t) = b × exp(a × t)
        Power: μ(t) = b × t a
        Logarithm: μ(t) = a × ln(t) + b
        Lloyd-Lipow: μ(t) = a − (b/t)


        Args:
            pf_interval:
            pf_std:

        Returns:

        """

        x = np.arange(0, pf_interval + 1, 1)

        if self._pf_curve == "linear":
            # Prevent zero division error
            if pf_interval <= 0:
                m = 0
            else:
                m = (self._failed - self._perfect) / pf_interval

            b = self._perfect
            y = m * x + b

        elif self._pf_curve == "step":
            y = np.append(np.full(pf_interval, self._perfect), (np.array(self._failed)))

        elif self._pf_curve == "exponential":
            raise NotImplementedError
        elif self._pf_curve == "exp":
            raise NotImplementedError

        return y

    def is_failed(
        self, t_start: int = None, t_end: int = None, cause: str = None
    ) -> List:
        """
        Determines if an indicator has failed between a time range from a cause

        Args:
            t_start: Optional; The time to start checking the failure
            t_end: Optional; The time to stop checking the failure
            cause: Optional; Consider the failure based on the impact of this cause only

        Returns:
            A list of boolean
        """

        timeline = self.get_timeline(cause)[t_start:t_end]

        # Check for failure
        if self.decreasing == True:
            failed = timeline <= self.threshold_failure
        else:
            failed = timeline >= self.threshold_failure

        return failed

    def reset_any(
        self, t_reset, target=0, method="reset", axis="time", permanent=False
    ):
        """
        # TODO make this work for all the renewal processes (as-bad-as-old, as-good-as-new, better-than-old, grp)
        """

        # Error with time reset, different method required.

        if method == "reduction_factor":
            accumulated = self.get_accumulated() * (1 - target)

        elif method == "reverse":

            accumulated = self.get_accumulated() - target

        elif method == "set":
            accumulated = target

        # Calculate the accumulated condition TODO not working
        if axis == "time":

            NotImplemented

        elif axis == "condition":

            """if self.decreasing:
                accumulated = min(max(self._failed, accumulated), self._perfect)
            else:
                accumulated = max(min(self._failed, accumulated), self._perfect)"""

            self._reset_accumulated(accumulated, permanent=permanent)

    def get_timeline(self, cause=None):
        # maybe add t_start?
        """ Returns the timeline for a name if it is in the key or if no key is passed and None is not a key, it aggregates all timelines"""
        if cause in self._timeline:
            timeline = self._timeline[cause]
        elif cause is None:
            timeline = self.agg_timeline()
        else:
            raise KeyError(
                "Name - %s - is not in %s %s timeline"
                % (name, self.__class__.__name__, self.name)
            )

        return timeline

    def agg_timeline(self, cause=None):
        """Aggregates all causes of condition loss and"""
        accumulated = np.array(list(self._accumulated.values())).sum(axis=0)

        if self.decreasing:
            timeline = self._perfect - accumulated
            timeline[timeline < self._failed] = self._failed
        else:
            timeline = self._perfect + accumulated
            timeline[timeline > self._failed] = self._failed

        return timeline

    def agg_timelines(self):
        """
        Takes a dictionary of timelines and returns the aggregated timelines
        """
        agg_timeline = []
        for timeline in self._timelines.values():
            if self.decreasing:
                etl = self._perfect - (
                    self._perfect - np.array(list(timeline.values()))
                ).sum(axis=0)
                etl[etl < self._failed] = self._failed
            else:
                etl = self._perfect + (
                    np.array(list(timeline.values())) - self._perfect
                ).sum(axis=0)
                etl[etl > self._failed] = self._failed

            agg_timeline.append(etl)

        return np.stack(agg_timeline)


class ConditionIndicator(Indicator):

    # Class Variables
    PF_CURVES = ["linear", "step"]

    def __init__(self, name: str = "ConditionIndicator", **kwargs):
        super().__init__(name=name, **kwargs)

        self.pf_curve_params = NotImplemented  # TODO for complex condition types

        # Current accumulation
        self._accumulated = dict()
        self._set_accumulated(accumulated=abs(self._perfect - self._initial))

    # ********************** Timeline methods ******************************

    def mc_timeline(self, t_end, t_start=0, n_iterations=100):
        for i in range(n_iterations):
            self.sim_timeline(t_start=t_start, t_stop=t_end)
            self.save_timeline()
            self.reset_for_next_sim()

    def sim_timeline(
        self,
        t_stop=None,
        t_delay=0,
        t_start=0,
        pf_interval=None,
        pf_std=0,
        name=None,
    ):
        """
        Returns the timeline that considers all the accumulated degradation and save timeline
        """
        # TODO make the t_delay more elegeant and remove duplication from failure_mode

        if name not in self._timeline:
            self._timeline[name] = self._sim_timeline(
                t_start=t_start, t_stop=t_stop, pf_interval=pf_interval, name=name
            )

        else:
            if t_delay is None:
                t_delay = 0

            self._timeline[name][t_delay:] = self._sim_timeline(
                t_start=t_start,
                t_stop=t_stop,
                pf_interval=pf_interval,
                pf_std=pf_std,
                name=name,
            )

        return self._timeline[name][t_delay:]

    def _sim_timeline(
        self, t_stop=None, t_start=0, pf_interval=None, pf_std=None, name=None
    ):
        """
        Returns the timeline that considers all the accumulated degradation
        """

        # Use the condition parameters if unique parameters aren't provided TODO maybe remove
        if pf_interval is None:
            pf_interval = self._pf_interval

        if pf_std is None:
            pf_std = self.pf_std

        # Adjust the pf_interval based on the expected variance in pf_std
        if pf_std is not None and pf_std != 0:
            pf_interval = int(pf_interval + round(ss.norm.rvs(loc=0, scale=pf_std)))

        # Set the condition profile if it hasn't been created already or if uncertainty is needed
        if pf_interval not in self._profile:
            self._set_profile(pf_interval=pf_interval, name=name)

        # Get the timeline
        timeline = self._acc_timeline(
            t_start=t_start, t_stop=t_stop, pf_interval=pf_interval
        )  # , name=name

        return timeline

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
            perfect = self._perfect

        if failed is None:
            failed = self._failed

        if pf_interval is None:
            pf_interval = self._pf_interval

        if pf_std is None:
            pf_std = self.pf_std

        x = np.arange(0, pf_interval + 1, 1)

        if self._pf_curve == "linear":
            # Prevent zero division error
            if pf_interval <= 0:
                m = 0
            else:
                m = (failed - perfect) / pf_interval
            b = perfect
            y = m * x + b

        elif self._pf_curve == "step":
            y = np.append(np.full(pf_interval, self._perfect), (np.array(self._failed)))

        elif self._pf_curve == "exponential" or self._pf_curve == "exp":
            raise NotImplementedError

        self._profile[pf_interval] = y

    def _acc_timeline(self, t_start=0, t_stop=None, pf_interval=None, name=None):
        # TODO this probably needs a delay?
        """
        Returns the timeli
        """

        # Validate times
        t_max = pf_interval  # len(self._profile[pf_interval]) - 1
        if t_stop is None:
            t_stop = t_max

        if t_start > t_stop:
            t_start = t_stop

        if t_stop < -1:  # TODO rewrite this
            t_start = t_start - t_stop
            t_stop = -1

        profile = self._profile[pf_interval][
            max(0, min(t_start, t_max)) : min(t_stop, t_max) + 1
        ]

        # Adjust for the accumulated condition
        accumulated = self.get_accumulated(name=name)
        if accumulated > 0:
            profile = profile - accumulated
            profile[profile < self._failed] = self._failed

        # Fill the start with the current condtiion
        if t_start < 0:
            if self.decreasing:
                current = self.perfect - accumulated
            else:
                current = accumulated

            profile = np.append(
                np.full(t_start * -1, current), profile
            )  # Changed from profile[0]

        # Fill the end with the failed condition
        n_after_failure = t_stop - t_start - len(profile) + 1
        if n_after_failure > 0:
            profile = np.append(profile, np.full(max(0, n_after_failure), self._failed))

        return profile

    def sim_failure_timeline(
        self,
        t_stop=None,
        t_delay=0,
        t_start=0,
        pf_interval=None,
        pf_std=None,
        name=None,
    ):
        # TODO this probably needs a delay? and can combine with condtion profile to make it simpler

        """
        Return a sample failure schedule for the condition
        """

        if self.decreasing == True:
            tl_f = self.get_timeline(name)[t_delay:] <= self.threshold_failure
        else:
            tl_f = self.get_timeline(name)[t_delay:] >= self.threshold_failure

        return tl_f

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
            return self._perfect - self.get_accumulated()
        else:
            return self._perfect + self.get_accumulated()

    def get_accumulated(self, name=None):  # TODO make this work for arrays of names
        """
        Returns the accumulated degradation
        """
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

    def set_t_condition(self, t, name=None):
        """ Set the condition base on a time t"""
        condition = float(self.get_timeline(name)[t])
        self.set_condition(condition, name)

    def set_condition(self, condition, name=None):
        """ Set the condition based on a condition"""
        # TODO consider impact of other impacts

        if self.decreasing:
            accumulated = min(
                max(0, self._perfect - condition), self._perfect - self._failed
            )
        else:
            accumulated = min(
                max(0, condition - self._perfect), self._failed - self._perfect
            )

        self._set_accumulated(accumulated=accumulated, name=name)

    def _set_accumulated(self, accumulated, name=None):
        """
        Add the accumulated degradation checking that it won't exceed the limits given intial condition
        """
        # check accumulated will not exceed the maximum allowable condition
        current = self.get_accumulated()

        # max accumulation - current - initial
        self._accumulated[name] = self.get_accumulated(name=name) + min(
            accumulated,
            abs(self._perfect - self._failed) - current,
        )

    def _reset_accumulated(self, accumulated=0, name=None, permanent=False):
        """
        Reset the accumulated condition with an option to add permanent condition loss
        """

        # Maintain permanent condition loss if set
        if permanent:
            accumulated = accumulated + self._accumulated.get("permanent", 0)
            name = "permanent"

        self._accumulated = dict()
        self._set_accumulated(name=name, accumulated=accumulated)

    def reset(self, name=None):

        super().reset()
        self._reset_accumulated()
        self._timeline = dict()

    def reset_for_next_sim(self, name=None):
        self._reset_accumulated(
            accumulated=abs(self._perfect - self._initial),
            permanent=False,
        )
        self._timeline = dict()

    def reset_to_perfect(self):
        self._reset_accumulated()

    def reset_any(self, target=0, method="reset", axis="time", permanent=False):
        """
        # TODO make this work for all the renewal processes (as-bad-as-old, as-good-as-new, better-than-old, grp)
        """

        # Error with time reset, different method required.

        if method == "reduction_factor":
            # accumulated = (abs(self._perfect - self.get_accumulated())) * (1 - target)
            accumulated = self.get_accumulated() * (1 - target)

        elif method == "reverse":

            accumulated = self.get_accumulated() - target

        elif method == "set":
            accumulated = target

        # Calculate the accumulated condition TODO not working
        if axis == "time":

            NotImplemented

        elif axis == "condition":

            """if self.decreasing:
                accumulated = min(max(self._failed, accumulated), self._perfect)
            else:
                accumulated = max(min(self._failed, accumulated), self._perfect)"""

            self._reset_accumulated(accumulated, permanent=permanent)

    def expected_condition(self, conf=0.5):
        ec = self.agg_timelines()
        return self._expected_condition(ec, conf)

    @classmethod
    def demo(cls):
        return cls.from_dict(demo.condition_data["slow_degrading"])


# TODO overload get method so the None key isnt' needed for _timeline
class PoleSafetyFactor(Indicator):

    # Class Variables
    PF_CURVES = ["ssf_calc", "dsf_calc"]

    def __init__(
        self,
        name="PoleSafetyFactor",
        perfect: int = 4,
        failed: int = 1,
        component=None,
        *args,
        **kwargs,
    ):
        super().__init__(name=name, perfect=perfect, failed=failed, *args, **kwargs)

    def set_t_condition(self, *args, **kwargs):
        """No actions required"""
        None

    def link_component(self, component):
        self.component = component

    def sim_timeline(self, t_delay=0, *args, **kwargs):
        """
        Overload safety factor
        """
        self._timeline[None] = self.safety_factor("simple")
        return self._timeline[None][t_delay:]

    def sim_failure_timeline(self, t_delay=0, *args, **kwargs):
        if self.decreasing == True:
            tl_f = self.get_timeline()[t_delay:] <= self.threshold_failure
        else:
            tl_f = self.get_timeline()[t_delay:] >= self.threshold_failure

        return tl_f

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
                agd=self.component.indicator["external_diameter"].perfect,
                czd=self.component.indicator["external_diameter"].get_timeline(),
                wt=self.component.indicator["wall_thickness"].get_timeline(),
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

        # Supress divide by zero error and fill na with zero
        with np.errstate(divide="ignore", invalid="ignore"):
            sf = margin * (czd ** 4 - (czd - 2 * wt) ** 4) / (czd * agd ** 3)
            sf[np.isnan(sf)] = 0

        return sf

    def expected_condition(self, conf=0.5):
        ec = self.agg_timelines()
        return self._expected_condition(ec, conf)


if __name__ == "__main__":
    indicator = Indicator()
    print("Indicator - Ok")
