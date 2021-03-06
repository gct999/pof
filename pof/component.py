"""

Author: Gavin Treseder
"""

# ************ Packages ********************
import copy
import logging
from typing import Dict

import numpy as np
import pandas as pd
from tqdm.notebook import tqdm
import json
import scipy.stats as ss

# Change the system path if an individual file is being run
if __package__ is None or __package__ == "":
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import config
from pof.failure_mode import FailureMode
from pof.helper import fill_blanks
from pof.indicator import Indicator
from pof.pof_base import PofBase
from pof.pof_container import PofContainer
import pof.demo as demo
from pof.interface.figures import (
    make_ms_fig,
    make_sensitivity_fig,
    update_pof_fig,
    update_condition_fig,
    make_task_forecast_fig,
    make_pop_table_fig,
    make_table_fig,
)
from pof.loader.asset_data import SimpleFleet
from pof.loader.asset_model_loader import AssetModelLoader
from pof.paths import Paths
from pof.units import scale_units, unit_ratio
from pof.decorators import coerce_arg_type

DEFAULT_ITERATIONS = 10

cf = config.get("Component")
cf_main = config.get("Main")


class Component(PofBase):
    """
    Parameters:

    Methods:


    Usage:


    """

    TIME_VARIABLES = []
    POF_VARIABLES = ["indicator", "fm"]

    def __init__(
        self,
        name: str = "comp",
        active: bool = True,
        indicator: Dict = None,
        fm: Dict = None,
        *args,
        **kwargs,
    ):

        super().__init__(name=name, *args, **kwargs)

        # self.fleet_data = "temp fix until creating asset class"

        self.active = active
        self.indicator = PofContainer()
        self.fm = PofContainer()

        self.set_indicator(indicator)
        self.set_failure_mode(fm)

        # Link failure mode indicators to the component indicators
        self.link_indicators()

        # Simulation traking
        self._in_service = True
        self._sim_counter = 0
        self._t_in_service = []
        self.stop_simulation = False

        # Dash Tracking
        self.up_to_date = True
        self.n = 0
        self.n_sens = 0
        self.n_iterations = 10
        self.n_sens_iterations = 10

        # Reporting
        self.df_pof = None
        self.df_cond = None
        self.df_erc = None
        self.df_sens = None
        self.df_task = None

    # ****************** Load data ******************

    # def load_asset_data(
    #     self,
    # ):

    #     # TODO Hook up data
    #     self.info = dict(
    #         pole_load=10,
    #         pole_strength=20,
    #     )

    #     # Set perfect indicator values?? TODO

    #     # Set indicators
    #     for indicator in self.indicator.values():

    #         # Set perfect

    #         # Set current
    #         raise NotImplementedError

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value):
        """ Set the pf_curve to a valid str"""

        if isinstance(value, str):
            if value.to_lower() in ["ok", "true", "yes"]:
                self._active = True
            elif value.to_lower() in ["false", "no"]:
                self._active = False
            else:
                raise ValueError("invalid acitve value")
        else:
            self._active = bool(value)

    def set_indicator(self, indicator_input):
        """Takes a dictionary of Indicator objects or indicator data and sets the component indicators"""
        self.set_obj("indicator", Indicator, indicator_input)

    def set_failure_mode(self, fm_input):
        """
        Takes a dictionary of FailureMode objects or FailureMode data and sets the component failure modes
        """
        self.set_obj("fm", FailureMode, fm_input)

    def link_indicators(self):

        for fm in self.fm.values():
            fm.set_indicators(self.indicator)

        # TODO move this logic of an indicator manager
        for ind in self.indicator.values():
            if ind.__class__.__name__ == "PoleSafetyFactor":
                ind.link_component(self)

    # ****************** Set data ******************
    # @coerce_arg_type
    # def mc(self, t_end: int, t_start: int = 0, n_iterations: int = DEFAULT_ITERATIONS):
    #     """ Complete MC simulation and calculate all the metrics for the component"""

    #     # Simulate a timeline
    #     self.mp_timeline(t_end=t_end, t_start=t_start, n_iterations=n_iterations)

    #     # Produce reports
    #     self.expected_risk_cost_df(t_end=t_end)
    #     self.calc_pof_df(t_end=t_end)
    #     # self.calc_df_task_forecast()
    #     self.calc_df_cond(t_start=t_start, t_end=t_end)

    #     return NotImplemented

    # ****************** Timeline ******************

    def cancel_sim(self):
        """ Pass a poison pill to end a simulation early and reset progress  """
        self.up_to_date = False
        self.n = 0
        self.n_sens = 0

    def mp_timeline(self, t_end, t_start=0, n_iterations=DEFAULT_ITERATIONS):
        """ Simulate the timeline mutliple times and exit immediately if updated"""
        self.reset()
        self.up_to_date = True
        self.n = 0
        self.n_iterations = n_iterations

        try:
            for __ in tqdm(range(self.n_iterations), desc="Simulation", leave=False):
                if not self.up_to_date:
                    break

                # Complete a simulation
                self.sim_timeline(t_end=t_end, t_start=t_start)
                self.save_timeline(self.n)
                self.increment_counter()
                self.reset_for_next_sim()

                self.n += 1
        except Exception as error:
            if self.up_to_date:
                raise error
            else:
                logging.warning("Error caught during cancel_sim")

    def mc_timeline(self, t_end, t_start=0, n_iterations=DEFAULT_ITERATIONS):
        """ Simulate the timeline mutliple times"""
        self.reset()

        for i in tqdm(range(n_iterations), desc="Simulation", leave=False):
            self.sim_timeline(t_end=t_end, t_start=t_start)
            self.save_timeline(i)
            self.increment_counter()
            self.reset_for_next_sim()

    def sim_timeline(self, t_end, t_start=0):
        """ Simulates the timelines for all failure modes attached to this component"""

        # Initialise the failure modes
        timeline = self.init_timeline(t_start=t_start, t_end=t_end)

        t_now = t_start
        self._in_service = True

        while t_now < t_end and self._in_service:

            t_next, next_fm_tasks = self.next_tasks(t_now)

            self.complete_tasks(t_next, next_fm_tasks)

            t_now = t_next + 1

        if self._in_service:
            self._t_in_service.append(t_now)

        return timeline

    def init_timeline(self, t_end, t_start=0):
        """ Initialise the timeline"""

        timeline = dict()

        for fm in self.fm.values():
            fm.init_timeline(t_start=t_start, t_end=t_end)

        return timeline

    def next_tasks(self, t_start=None):
        """
        Returns a dictionary with the failure mode triggered
        """
        # TODO make this more efficent
        # TODO make this work if no tasks returned. Expect an error now

        # Get the task schedule for next tasks
        task_schedule = dict()
        if self.active:
            for fm_name, fm in self.fm.items():

                t_next, task_names = fm.next_tasks(t_start=t_start)

                if t_next in task_schedule:
                    task_schedule[t_next][fm_name] = task_names
                else:
                    task_schedule[t_next] = dict()
                    task_schedule[t_next][fm_name] = task_names

            t_next = min(task_schedule.keys())

        return t_next, task_schedule[t_next]

    def complete_tasks(self, t_next, fm_tasks):
        """Complete any tasks in the dictionary fm_tasks at t_now"""

        # TODO add logic around all the different ways of executing
        # TODO check task groups
        # TODO check value?
        # TODO add task impacts

        system_impacts = []

        if self.active:

            for fm_name, task_names in fm_tasks.items():
                system_impact = self.fm[fm_name].complete_tasks(t_next, task_names)
                system_impacts = system_impacts + system_impact

                if (
                    "system" in system_impacts or "component" in system_impacts
                ) and cf.get("allow_system_impact"):
                    logging.debug(
                        "Component %s reset by FailureMode %s", self._name, fm_name
                    )
                    self.renew(t_renew=t_next + 1)

                    break

                # Ghetto fix TODO
                if "indicator" in system_impacts:
                    for fm in self.fm.values():
                        fm.update_timeline(t_next + 1, updates={"failure": False})

        return system_impacts

    def renew(
        self,
        t_renew,
    ):
        """
        Renew the component because a task has triggered an as-new change or failure
        """

        # Fail
        if config.get("FailureMode").get("remain_failed"):
            for fm in self.fm.values():
                fm.fail(t_renew)

            self._in_service = False

        # Replace
        else:
            for fm in self.fm.values():
                fm.renew(t_renew)

            # Reset the indicators
            for ind in self.indicator.values():
                ind.reset_to_perfect()

    def fail(self, t_fail):
        """ Cut the timeline short and prevent any more tasks from triggering"""

        self.in_service = False

        for fm in self.fm.values():
            fm.fail(t_fail)

    def increment_counter(self):
        self._sim_counter += 1

        for fm in self.fm.values():
            fm.increment_counter()

    def save_timeline(self, idx):
        for fm in self.fm.values():
            fm.save_timeline(idx)

        for ind in self.indicator.values():
            ind.save_timeline(idx)

    # ****************** Progress *******************

    def progress(self) -> float:
        """ Returns the progress of the primary simulation """
        return self.n / self.n_iterations

    def sens_progress(self) -> float:
        """ Returns the progress of the sensitivity simulation """
        return (self.n_sens * self.n_iterations + self.n) / (
            self.n_iterations * self.n_sens_iterations + self.n
        )

    # ****************** Expected ******************

    def population_table(self):
        """ Reports a summary of the in service, FF and CF outcomes over the MC simulation """
        pop_table = {}
        _ff = 0
        _cf = 0
        for fm in self.fm.values():
            _ff = _ff + len(fm.expected_ff())
            _cf = _cf + len(fm.expected_cf())
        pop_table["summary"] = {
            "is": self._sim_counter - _ff - _cf,
            "cf": _cf,
            "ff": _ff,
        }

        df_pop_summary = pd.DataFrame.from_dict(pop_table).T
        col_order = ["is", "cf", "ff"]
        df = df_pop_summary.reindex(columns=col_order)

        return df

    def expected_cf(self):
        """ Returns the conditional failures for the component """
        t_cf = []
        for fm in self.fm.values():
            t_cf.extend(fm.expected_cf())

        return t_cf

    def expected_ff(self):
        """Returns the functional failures for the component"""
        t_ff = []
        for fm in self.fm.values():
            t_ff.extend(fm.expected_ff())

        return t_ff

    def expected_life(self):
        e_l = (
            sum(self._t_in_service + self.expected_cf() + self.expected_ff())
            / self._sim_counter
        )

        return e_l

    def expected_untreated(self, t_start=0, t_end=100):

        sf = dict(all=dict(pof=np.full((t_end - t_start + 1), 1)))
        for fm in self.fm.values():
            sf[fm.name] = dict()
            sf[fm.name]["pof"] = fm.untreated.sf(t_start=t_start, t_end=t_end)
            sf[fm.name]["active"] = fm.active

            if fm.active:
                sf["all"]["pof"] = sf["all"]["pof"] * sf[fm.name]["pof"]
                sf["all"]["active"] = True

        # Treat the failure modes as a series and combine together
        # cdf = {fm: 1 - sf for fm, sf in sf.items()}
        cdf = dict()

        for fm in sf:
            cdf[fm] = dict()
            cdf[fm]["pof"] = 1 - sf[fm]["pof"]
            cdf[fm]["active"] = sf[fm]["active"]
            cdf[fm]["time"] = np.linspace(
                t_start, t_end, t_end - t_start + 1, dtype=int
            )

        return cdf

    def expected_pof(self, t_start=0, t_end=100):

        sf = self.expected_sf(t_start, t_end)

        cdf = dict()

        for fm in sf:
            cdf[fm] = dict()
            cdf[fm]["pof"] = 1 - sf[fm]["pof"]
            cdf[fm]["active"] = sf[fm]["active"]
            cdf[fm]["time"] = np.linspace(
                t_start, t_end, t_end - t_start + 1, dtype=int
            )

        return cdf

    def expected_sf(self, t_start=0, t_end=100):

        # Calcuate the failure rates for each failure mode
        sf = dict(all=dict(pof=np.full((t_end - t_start + 1), 1)))
        sf["all"]["active"] = False

        for fm_name, fm in self.fm.items():
            if fm.active:
                pof = fm.expected_pof()
                sf[fm_name] = dict()
                sf[fm_name]["pof"] = pof.sf(t_start, t_end)
                sf[fm_name]["active"] = fm.active

                sf["all"]["pof"] = sf["all"]["pof"] * sf[fm_name]["pof"]
                sf["all"]["active"] = True

        # Treat the failure modes as a series and combine together
        # sf['all'] = np.array([fm.sf(t_start, t_end) for fm in self.fm.values()]).prod(axis=0)

        # TODO Fit a new Weibull for the new failure rate....

        return sf

    def expected_risk_cost_df(self, t_start=0, t_end=None):
        """ A wrapper for expected risk cost that returns a dataframe"""
        erc = self.expected_risk_cost()

        if t_end == None:
            t_end = t_start
            for timeline in erc.values():
                for task in timeline.values():
                    if isinstance(task, bool):
                        continue
                    else:
                        t_end = max(max(task["time"], default=t_start), t_end)

        df = pd.DataFrame().from_dict(erc, orient="index")
        df.index.name = "failure_mode"
        df = df.reset_index().melt(id_vars="failure_mode", var_name="task")
        df = pd.concat(
            [df.drop(columns=["value"]), df["value"].apply(pd.Series)], axis=1
        )[
            [
                "failure_mode",
                "task",
                "active",
                "time",
                "quantity",
                "cost",
            ]
        ].dropna()

        # Fill in the missing dates for plotting purposes
        fill_cols = ["cost", "quantity"]  # time not needed
        df_filled = df.apply(fill_blanks, axis=1, args=(t_start, t_end, fill_cols))
        df = df_filled.explode("time")

        for col in fill_cols:
            df[col] = df_filled.explode(col)[col]
            df[col + "_cumulative"] = df.groupby(by=["failure_mode", "task"])[
                col
            ].transform(pd.Series.cumsum)
            df[col + "_annual"] = df[col] / self.expected_life()

            df[col + "_lifecycle"] = df[col + "_cumulative"] / self.expected_life()

        # Formatting
        self.df_erc = sort_df(df=df, column="task")

        return self.df_erc

    def expected_risk_cost_df_legacy_method(self, t_start=0, t_end=None):
        """ A wrapper for expected risk cost that returns a dataframe"""

        # TODO encapsualte in failure_mode and task

        # Create the erc_df
        d_comp = {}
        for fm in self.fm.values():
            d_fm = {}
            for task in fm.tasks.values():
                d_fm[task.name] = pd.DataFrame(task.expected_costs())
            df_fm = (
                pd.concat(d_fm, names=["source", "drop"])
                .reset_index()
                .drop("drop", axis=1)
            )
            d_comp[fm.name] = df_fm

        df_comp = (
            pd.concat(d_fm, names=["failure_mode", "drop"])
            .reset_index()
            .drop("drop", axis=1)
        )

        # Get the desired time steps
        t_start = 0  # int(df_comp['time'].min()) if t_start is None
        # t_end = t_end  # int(df_comp['time'].max()) if t_end is None
        time = np.linspace(t_start, t_end, t_end - t_start + 1).astype(int)

        df = df_comp[["failure_mode", "source", "active"]].drop_duplicates()
        df_time = pd.DataFrame({"time": time})

        # Cross join
        df["key"] = 1
        df_time["key"] = 1
        df = pd.merge(df, df_time, on="key")
        df = pd.merge(
            df, df_fm, on=["failure_mode", "source", "time", "active"], how="left"
        ).drop("key", axis=1)

        # Fill blanks
        df["cost"].fillna(0, inplace=True)

        # Calculate other forms of cost
        df["cost_cumulative"] = df.groupby(by=["failure_mode", "source"])[
            "cost"
        ].transform(pd.Series.cumsum)

        return df

    def expected_risk_cost(self):
        return {fm.name: fm.expected_risk_cost() for fm in self.fm.values()}

    def expected_condition(self, conf=0.95):
        """ Returns the expected condition for all indicators associated with active failure modes"""
        expected = {}

        for fm in self.fm.values():
            if fm.active:
                for ind_name in fm._cond_to_update():
                    if ind_name not in expected:
                        expected[ind_name] = fm.indicators[ind_name].expected_condition(
                            conf
                        )

        return expected

    # **************** Interface ********************

    def expected_sensitivity(
        self,
        var_id,
        lower,
        upper,
        step_size=1,
        n_iterations=100,
        t_end=100,
        rolling_window=None,
    ):
        """
        Returns dataframe of sensitivity data for a given variable name using a given lower, upper and step_size.
        """
        rc = dict()
        self.reset()

        # Progress bars
        self.n_sens = 0
        self.n_sens_iterations = int((upper - lower) / step_size + step_size)

        prefix = ["quantity", "cost"]
        suffix = ["", "_annual", "_cumulative", "_lifecycle"]
        cols = [f"{pre}{suf}" for pre in prefix for suf in suffix]

        for i in tqdm(np.arange(lower, upper + step_size, step_size), desc=var_id):
            if not self.up_to_date:
                return "sim cancelled"
            try:
                # Reset component
                self.reset()

                # Update annd simulate a timeline
                if isinstance(var_id, list):
                    var = var_id
                    for v_id in var_id:
                        self.update(v_id)
                else:
                    var = var_id.split("-")[-1]
                    self.update(var_id, i)

                self.mp_timeline(t_end=t_end, n_iterations=n_iterations)
                df_rc = self.expected_risk_cost_df()

                # Summarise outputs
                df_rc = df_rc.groupby(by=["task", "active"])[cols].max()
                df_rc[var] = i

                rc[i] = df_rc

                self.n_sens = self.n_sens + 1

            except Exception as error:
                logging.error("Error at %s", exc_info=error)

        self.df_sens = (
            pd.concat(rc)
            .reset_index()
            .drop(["level_0"], axis=1)
            .rename(columns={"task": "source"})
        )

        return self.df_sens

    def sensitivty_chain(
        self, sens_vars: dict, n_iterations: int = 100, t_end: int = 100
    ):
        """Recursively solve the sensitivity for the all the vars being tested

        Args:
            sens_vars: the variable id and values that will be adjusged
            n_iterations: the number of iterations that are completed per simulation
            t_end: the length of the time the each iteration is simulated

        Returns:
            df_sens: A dataframe of expected risk costs by failure mode and task for each combination of sens_vars
        """

        # Create copy so original isn't changed
        sens_vars = copy.deepcopy(sens_vars)

        if not sens_vars:  # Calculate the sensitivity

            # Format
            prefix = ["quantity", "cost"]
            suffix = ["", "_annual", "_cumulative", "_lifecycle"]
            cols = [f"{pre}{suf}" for pre in prefix for suf in suffix]

            # Simulate
            self.reset()
            self.mp_timeline(t_end=t_end, n_iterations=n_iterations)

            # Report
            df_sens = self.expected_risk_cost_df()
            df_sens = df_sens.groupby(by=["task", "active"])[cols].max().reset_index()

        else:  # Recurisvely call the same function
            results = dict()

            var_id = next(iter(sens_vars))
            sens_range = sens_vars.pop(var_id)

            for update_val in tqdm(sens_range, desc=var_id):

                self.update(var_id, update_val)

                results[update_val] = self.sensitivty_chain(
                    sens_vars, t_end=t_end, n_iterations=n_iterations
                )
                results[update_val][var_id] = update_val

            df_sens = pd.concat(results, ignore_index=True)

        return df_sens

    # ****************** Reports ****************

    def calc_df_erc(self):
        if self.up_to_date:
            if self.df_erc is not None:
                df_erc = self.df_erc
            else:
                self.df_erc = self.expected_risk_cost_df()

        raise NotImplementedError()

    def calc_pof_df(self, t_end=None):
        # TODO this could be way more efficient
        pof = dict(
            maint=pd.DataFrame(self.expected_pof(t_end=t_end)),
            no_maint=pd.DataFrame(self.expected_untreated(t_end=t_end)),
        )

        # OLD CODE
        # df = pd.concat(pof).rename_axis(["strategy", "time"]).reset_index()
        # df.index.names = ["strategy", "key"]
        # df = df.rename(columns={"variable": "source"})

        # df = df.melt(
        #     id_vars=["time", "strategy", "fm_active"],
        #     var_name="source",
        #     value_name="pof",
        # )

        df = pd.concat(pof).rename_axis(["strategy", "key"]).reset_index()

        df_pof = df[df["key"] == "pof"]
        df_pof = pd.melt(
            df_pof, id_vars=["strategy"], value_vars=df_pof.columns[2:]
        ).rename(columns={"variable": "source", "value": "pof"})
        df_pof = df_pof.explode("pof", ignore_index=True)

        df_active = df[df["key"] == "active"]
        df_active = pd.melt(
            df_active, id_vars=["strategy"], value_vars=df_active.columns[2:]
        ).rename(columns={"variable": "source", "value": "active"})

        df_time = df[df["key"] == "time"]
        df_time = pd.melt(
            df_time, id_vars=["strategy"], value_vars=df_time.columns[2:]
        ).rename(columns={"variable": "source", "value": "time"})
        df_time = df_time.explode("time", ignore_index=True)["time"]

        df = df_pof.merge(df_active, on=["strategy", "source"])
        df["time"] = df_time

        self.df_pof = df

        return self.df_pof

    def calc_df_task_forecast(self, df_age_forecast, age_units="years"):
        """Create the task plot dataframe
        age_units - the units for the age in df_forecast age
        """

        # Scale the units to match the desired outputs
        df_age_forecast, __ = scale_units(df_age_forecast, self.units, age_units)

        # Convert to floats for merging
        # TODO deep copy not needed anymore
        df_erc = copy.deepcopy(self.df_erc)
        df_erc["time"] = df_erc["time"].astype(float)
        df_age_forecast["age"] = df_age_forecast["age"].astype(float)

        # Duplicate time so the closest age can be used
        df_age_forecast["time"] = df_age_forecast["age"]

        df_erc = pd.merge_asof(
            df_erc.sort_values("time"),
            df_age_forecast.sort_values("age")[["age", "time"]],
            on="time",
            tolerance=unit_ratio(age_units, self.units),
        )

        # Merge the population details
        df = pd.merge(
            df_erc.sort_values("age"),
            df_age_forecast.sort_values("age"),
            left_on="age",
            right_on="age",
        )

        # Calculated population outcomes
        df["pop_quantity"] = df["assets"] * df["quantity"]
        df["pop_cost"] = df["pop_quantity"] * df["cost"]

        # Regroup into a task forecast
        df = (
            df.groupby(by=["year", "task", "active"])[["pop_quantity", "pop_cost"]]
            .sum()
            .reset_index()
        ).dropna()

        self.df_task = sort_df(df=df, column="task")

        return self.df_task

    def calc_df_cond(self, t_start=0, t_end=None):

        # TODO fix this so that it isn't being repeated

        ecl = self.expected_condition()

        df = pd.DataFrame()
        i = 1
        for cond_name, cond in ecl.items():
            data = np.append(cond["upper"], cond["lower"][::-1])
            df["y" + str(i)] = data
            i = i + 1

            # TODO temp fix that won't work for t_start
            time = np.arange(t_start, t_end + 1, 1).tolist()
            df["time"] = np.append(time, time[::-1])

        self.df_cond = df

        return self.df_cond

    def calc_summary(self, df_cohort=None, cohort_units=None):
        """ Reports a summary for each of the failure modes and the expected outcomes over the MC simulation"""
        # Get the key data from each of the failuremodes
        summary = {}

        for fm in self.fm.values():
            if fm.active:
                insp_effective = fm.inspection_effectiveness()
                _ff = fm.expected_ff()
                _cf = fm.expected_cf()

                summary[fm.name] = {
                    "fm": fm.name,
                    "ie": insp_effective,
                    "is": self._sim_counter - len(_cf) - len(_ff),
                    "ff": len(_ff),
                    "cf": len(_cf),
                }

                if df_cohort is not None:

                    f_names = ["cf", "ff"]
                    f_ages = [_cf, _ff]
                    for f_name, f_age in zip(f_names, f_ages):
                        age, count = np.unique(f_age, return_counts=True)

                        # Scale age based on the units
                        # TODO this will need to be fixed so its works ith units in all direction *UR as int * UR
                        age = (age * unit_ratio(self.units, cohort_units)).astype(int)

                        # Total failures
                        total_failed = (
                            df_cohort.reindex(age).mul(count, axis=0).sum()[0]
                            / self._sim_counter
                        )

                        lower, upper = calc_confidence_interval(
                            sim_counter=self._sim_counter,
                            df_cohort=df_cohort,
                            total_failed=total_failed,
                        )

                        summary[fm.name][f_name + " pop annual avg"] = total_failed
                        summary[fm.name]["conf interval " + f_name + " (+/-)"] = (
                            total_failed - lower
                        )

        df = pd.DataFrame.from_dict(summary).T

        # Calculate the total row and append to the df
        total = {
            "fm": "total",
            "ie": df["ie"].prod(),
            "is": self._sim_counter - df[["ff", "cf"]].sum().sum(),
            "ff": df["ff"].sum(),
            "cf": df["cf"].sum(),
        }
        df = df.append(total, ignore_index=True).set_index("fm")

        # Calculate simulated effectiveness
        mask_failures = (df["cf"] != 0) & (df["cf"] != 0)
        df["prevented"] = df.loc[mask_failures, "cf"] / df.loc[
            mask_failures, ["cf", "ff"]
        ].sum(axis=1)

        df["prevented"].fillna("")

        # Add the cohort data if it is supplied
        if df_cohort is not None:
            df.loc["total", "cf pop annual avg"] = df["cf pop annual avg"].sum()
            df.loc["total", "ff pop annual avg"] = df["ff pop annual avg"].sum()

        # Format for display
        col_order = [
            "fm",
            "ie",
            "is",
            "cf",
            "ff",
            "prevented",
            "cf pop annual avg",
            "conf interval cf (+/-)",
            "ff pop annual avg",
            "conf interval ff (+/-)",
        ]
        df = df.reset_index().reindex(columns=col_order)

        percent_col = ["ie", "prevented"]
        df[percent_col] = df[percent_col].mul(100)
        rename_cols = {col: col + " (%)" for col in percent_col}
        df.rename(columns=rename_cols, inplace=True)

        return df

    # ***************** Figures *****************

    # TODO change default to first value from const

    def plot_ms(
        self,
        y_axis="cost_cumulative",
        keep_axis=False,
        units: str = None,
        prev=None,
    ):
        """ Returns a cost figure if df has aleady been calculated"""
        # TODO Add conversion for units when plotting if units != self.units

        df, units = scale_units(
            df=self.df_erc, input_units=units, model_units=self.units
        )

        return make_ms_fig(
            df=df,
            y_axis=y_axis,
            keep_axis=keep_axis,
            units=units,
            prev=prev,
        )

    def plot_pof(self, keep_axis=False, units=None, prev=None):
        """ Returns a pof figure if df has aleady been calculated"""

        df, units = scale_units(
            df=self.df_pof, input_units=units, model_units=self.units
        )

        return update_pof_fig(df=df, keep_axis=keep_axis, units=units, prev=prev)

    def plot_cond(self, keep_axis=False, units=None, prev=None):
        """ Returns a condition figure if df has aleady been calculated"""

        df, units = scale_units(
            df=self.df_cond, input_units=units, model_units=self.units
        )

        return update_condition_fig(
            df=df,
            ecl=self.expected_condition(),
            keep_axis=keep_axis,
            units=units,
            prev=prev,
        )

    def plot_task_forecast(
        self,
        keep_axis=False,
        prev=None,
    ):
        """ Return a task figure if df has aleady been calculated """

        return make_task_forecast_fig(
            df=self.df_task,
            keep_axis=keep_axis,
            prev=prev,
        )

    def plot_sens(
        self,
        y_axis="cost_cumulative",
        keep_axis=False,
        units=None,
        var_id="",
        prev=None,
    ):
        """ Returns a sensitivity figure if df_sens has aleady been calculated"""
        var_name = var_id.split("-")[-1]

        df_plot = self.sens_summary(var_name=var_name)

        df = sort_df(
            df=df_plot, column="source", var=var_name
        )  # Sens ordered here as x var is needed

        df, units = scale_units(df, input_units=units, model_units=self.units)

        return make_sensitivity_fig(
            df_plot=df,
            var_name=var_name,
            y_axis=y_axis,
            keep_axis=keep_axis,
            units=units,
            prev=prev,
        )

    def sens_summary(self, var_name="", summarise=True):
        """ Add direct and total to df_sens for the var_id and return the df to plot """
        # if summarise: #TODO

        df = self.df_sens

        # Add direct and indirect
        df_total = df.groupby(by=[var_name]).sum()
        df_direct = (
            df_total - df.loc[df["source"] == "risk"].groupby(by=[var_name]).sum()
        )
        summary = {
            "total": df_total,
            "direct": df_direct,
            # "risk": df.loc[df["source"] == "risk"],
        }

        df_plot = pd.concat(summary, names=["source"]).reset_index()
        df_plot["active"] = df_plot["active"].astype(bool)
        df_plot = df_plot.append(df)
        # df_plot = df_plot.append(df.loc[df["source"] != "risk"])

        return df_plot

    # def plot_pop_table(self):

    #     df = self.population_table()
    #     fig = make_pop_table_fig(df)

    #     return fig

    def plot_summary(self, df_cohort=None, cohort_units=None):

        # TODO move calc step earlier to alight with simulate, report, plot philosophy
        df = self.calc_summary(df_cohort=df_cohort, cohort_units=cohort_units)

        # Formatting
        title = "Forecast Summary"
        if df_cohort is not None:
            population = df_cohort["assets"].sum()
            title += f" (Population: {population})"

        fig = make_table_fig(df, title=title)

        return fig

    # ****************** Reset ******************

    def reset_condition(self):

        for fm in self.fm.values():
            fm.reset_condition()

    def reset_for_next_sim(self):
        """ Reset parameters back to the initial state"""

        for fm in self.fm.values():
            fm.reset_for_next_sim()

    def reset(self):
        """ Reset all parameters back to the initial state and reset sim parameters"""

        # Reset failure modes
        for fm in self.fm.values():
            fm.reset()

        # Reset counters
        self._sim_counter = 0
        self._t_in_service = []
        self.stop_simulation = False

        # Reset stored reports
        self.df_erc = None
        self.df_sens = None
        self.df_pof = None
        self.df_cond = None
        self.df_task = None

    # ****************** Interface ******************

    def update_from_dict(self, data):
        """ Adds an additional update method for task groups"""

        # Loop through all the variables to update
        for attr, detail in data.items():
            if attr == "task_group_name":
                self.update_task_group(detail)

            elif attr == "consequence":
                self.update_consequence(data)

            else:
                super().update_from_dict({attr: detail})

    def update_task_group(self, data):
        """ Update all the tasks with that task_group across the objects"""
        # TODO replace with task group manager

        for fm in self.fm.values():
            fm.update_task_group(data)

    def update_consequence(self, data):
        """ Update the consequence of any failure mode """
        # TODO replace with consequence group manager
        for fm in self.fm.values():
            fm.update_consequence(data)

    def get_dash_ids(self, numericalOnly: bool, prefix="", sep="-", active=None):
        """Return a list of dash ids for values that can be changed"""

        if active is None or (self.active == active):
            # Component
            prefix = prefix + self.name + sep
            comp_ids = [prefix + param for param in ["active"]]

            # Tasks
            fm_ids = []
            for fm in self.fm.values():
                fm_ids = fm_ids + fm.get_dash_ids(
                    numericalOnly=numericalOnly,
                    prefix=prefix + "fm" + sep,
                    sep=sep,
                    active=active,
                )

            # Indicators
            ind_ids = []
            for ind in self.indicator.keys():
                for param in cf.get("indicator_input_fields"):
                    ind_ids.append(prefix + "indicator" + sep + ind + sep + param)

            # Consequence
            cons_ids = [prefix + "consequence" + sep + "cost"]

            dash_ids = comp_ids + fm_ids + ind_ids + cons_ids
        else:
            dash_ids = []

        return dash_ids

    def get_update_ids(
        self, numericalOnly: bool = True, prefix="", sep="-", filter_ids: dict = None
    ):
        """ Get the ids for all objects that should be updated"""
        # TODO remove this once task groups added to the interface
        # TODO fix encapsulation

        ids = self.get_dash_ids(numericalOnly=numericalOnly, active=True, prefix=prefix)

        update_ids = dict()
        for fm in self.fm.values():
            for task in fm.tasks.values():
                if task.task_group_name not in update_ids:
                    update_ids[
                        task.task_group_name + "t_interval"
                    ] = f"{prefix}{self.name}{sep}task_group_name{sep}{task.task_group_name}{sep}t_interval"

                    update_ids[
                        task.task_group_name
                    ] = f"{prefix}{self.name}{sep}task_group_name{sep}{task.task_group_name}{sep}t_delay"

        ids = list(update_ids.values()) + ids
        return ids

    def get_objects(self, prefix="", sep="-"):

        objects = [prefix + self.name]

        prefix = prefix + self.name + sep

        for fms in self.fm.values():
            objects = objects + fms.get_objects(prefix=prefix + "fm" + sep)

        objects.append(prefix + "indicator")
        objects.append(prefix + "consequence")

        return objects

    # ****************** Demonstration parameters ******************

    @classmethod
    def demo(cls):
        """ Loads a demonstration data set if no parameters have been set already"""

        return cls.load(demo.component_data["pole"])


def sort_df(df=None, column=None, var=None):
    """
    sorts the dataframes for the graphs with total, risk and direct first
    """
    if column is None:
        raise ValueError("Column must be defined")

    # List distinct values in input column
    if column == "task":
        values = df["task"].unique().tolist()
        values.sort()
    elif column == "source":
        values = df["source"].unique().tolist()
        values.sort()

    # Create a list of columns to sort by
    if var is not None:
        columns = [var, column]
    elif "year" in df.columns.tolist():
        columns = ["year", column]
    elif "time" in df.columns.tolist():
        columns = ["time", column]
    else:
        columns = [column]

    # Define custom order required
    start_order = ["total", "risk", "direct"]
    set_order = []

    # Add custom columns to the set order
    for var in start_order:
        if var in values:
            set_order.append(var)

    # Add all other columns to set order alphabetically
    for var in values:
        if var not in set_order:
            set_order.append(var)

    # Create a dictionary of return order
    return_order = {}
    i = 1
    for var in set_order:
        return_order[var] = i
        i = i + 1

    # Sort by sort column list
    df[column] = pd.Categorical(df[column], return_order)
    ordered_df = df.sort_values(by=columns)

    return ordered_df


def calc_confidence_interval(sim_counter=None, df_cohort=None, total_failed=None):
    """ Calculate the upper and lower bounds for a given confidence interval """

    conf_interval = cf.get("forecast_confidence_interval")
    # Interval is 0.8 (80% confidence) - need to include both tails, so ppf(0.9)
    z_score = ss.norm.ppf(1 - (1 - conf_interval) / 2)

    # Calculate confidence interval
    population_total = df_cohort.sum()[0] / sim_counter

    p_failed = total_failed / population_total

    se_failed = np.sqrt(p_failed * (1 - p_failed) / population_total)

    lower_bound = (p_failed - z_score * se_failed) * population_total
    upper_bound = (p_failed + z_score * se_failed) * population_total

    return lower_bound, upper_bound


if __name__ == "__main__":
    component = Component()
    print("Component - Ok")

    """import doctest
    doctest.testmod()"""