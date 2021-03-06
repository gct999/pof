"""
    Filename: model_loader.py
    Description: Contains the code for implementing a ModelLoader class
    Author: Gavin Treseder | gct999@gmail.com | gtreseder@kpmg.com.au | gavin.treseder@essentialenergy.com.au
"""

import logging

import pandas as pd
import numpy as np
import json

from config import config

cf = config["AssetModelLoader"]
cf_main = config["Main"]


class AssetModelLoader:
    """
    ModelLoader is used to load model parameters from an excel sheet or a json file and transform them into a json/dict structure that can be used to load pof objects.


    Usage:

    aml = AssetModelLoader()
    aml.load(filename)
    """

    def __init__(
        self,
        filename=None,
    ):

        # file location
        self.filename = filename

    def load(self, filename=None):
        logging.info("Asset Model loading...")
        # Load a filename if it has been passed to it
        if filename is None:
            if self.filename is None:
                raise Exception("No file specified")
        else:
            self.set_filename(filename)

        # Load the data
        if filename[-4:] == "json":
            logging.info("Loading json file")
            data = self.load_json()
        else:
            logging.info("Loading excel file")
            data = self.load_xlsx()

        logging.info("Asset Model Loaded")
        return data

    def set_filename(self, filename):
        # TODO add some error checking around this

        self.filename = filename

    def load_xlsx(self):
        """
        Transform a .xlsx file into a dictionary which can be used to create an asset model
        """

        self.read_xlsx()
        if cf_main.get("system"):
            data = self._get_system_data(self.df)
        else:
            data = self._get_component_data(self.df)

        return data

    def read_xlsx(self):
        """
        Transform a .xlsx file into a dictionary which can be used to create an asset model
        """

        try:
            df = pd.read_excel(
                self.filename,
                sheet_name="Model Input",
                header=[0, 1, 2],
                engine="openpyxl",
            )
        except AttributeError:
            ddf = pd.read_excel(
                self.filename, sheet_name="Model Input", header=[0, 1, 2], engine="xlrd"
            )

        # Create keys
        keys = dict(
            asset_model=("asset_model", "component", "name"),
            # ('indicator_model', 'indicator','name'),
            failure_model=("failure_model", "failure_mode", "name"),
            task_model=("task_model", "task", "name"),
            # ('trigger_model', 'condition', 'name'), #TODO revist this one
            # ('impact_model', 'condition', 'name'),
        )

        # Replace nan with None
        df = df.replace({np.nan: None})

        # Drop rows with no data
        df = df.dropna(how="all")

        df = self.rename_keys(df=df, keys=keys)

        # Propogate keys for 1 to many relationships
        key_list = [key for key in keys.values()]
        df[key_list] = df[key_list].ffill()

        self.df = df

    def load_json(self):
        """
        Use a dictionary in a json file to create an asset model
        """
        try:
            with open(self.filename) as json_file:
                sys_data = json.load(json_file)

            self.df = pd.DataFrame.from_dict(sys_data)

            return sys_data

        except Exception as error:
            logging.error("Error saving file", exc_info=error)

    def load_pof_object(self):

        NotImplemented

    def to_xls(self):

        NotImplemented

    # ********************* validate methods *****************************

    def _validate_keys(self, keys, df):
        missing_keys = [key for key in keys if key not in df.columns]

        if bool(missing_keys):
            print("Missing Keys: %s" % (missing_keys))
            return False
        else:
            return True

    def _validate_unique_keys(self, keys, df):

        NotImplemented

    def rename_keys(self, df, keys):

        # Check Components aren't duplicated
        # TODO only uses

        # Check Failure Modes aren't duplicated
        key_cols = [keys["asset_model"], keys["failure_model"]]
        mask_key = df[key_cols].notnull().any(axis=1)
        mask_dup = df.loc[mask_key, key_cols].ffill().duplicated(keep=False)

        mask = mask_key & mask_dup
        df.loc[mask, keys["failure_model"]] += "_" + df[key_cols].loc[
            mask
        ].ffill().groupby(key_cols).cumcount().add(1).astype(str)

        # Check Tasks aren't duplicated
        key_cols = [keys["asset_model"], keys["failure_model"], keys["task_model"]]
        mask_key = df[key_cols].notnull().any(axis=1)
        mask_dup = df.loc[mask_key, key_cols].ffill().duplicated(keep=False)

        mask = mask_key & mask_dup
        df.loc[mask, keys["task_model"]] += "_" + df[key_cols].loc[
            mask
        ].ffill().groupby(key_cols).cumcount().add(1).astype(str)

        return df

    # ********************* excel load methods *****************************

    def _get_system_data(self, df):
        # Get the System information
        sys_key = ("asset_model", "system", "name")
        sys_list = df[sys_key].dropna().tolist()

        # Get the Component information
        comp_key = ("asset_model", "component", "name")
        comp_list = df[comp_key].dropna().unique().tolist()

        system_data = dict()

        # Create the keys for the systems and the components on each system
        for i in range(0, len(sys_list)):
            if not sys_list[i] in system_data:
                system_data[sys_list[i]] = dict()
            system_data[sys_list[i]][comp_list[i]] = dict()

        # Add the component dictionary onto the keys
        for system in system_data:
            comps_data = self._get_component_data(
                self.df, components=system_data[system]
            )

            sys_data = dict(name=system, comp=comps_data)
            system_data.update({system: sys_data})

        return system_data

    def _get_component_data(self, df, components=None):

        comps_data = dict()

        # Get the Component information
        comp_key = ("asset_model", "component", "name")
        if components == None:
            components = df[comp_key].dropna().unique()

        df_comps = df[
            [
                "asset_model",
                "failure_model",
                "indicator_model",
                "condition_model",
                "task_model",
                "trigger_model",
                "impact_model",
            ]
        ].set_index(comp_key)

        for comp in components:

            df_comp = df_comps.loc[[comp]]

            comp_data = (
                df_comp["asset_model"]["component"].dropna(how="all").iloc[0].to_dict()
            )

            # Get the FailureMode information
            fm_data = self._get_failure_mode_data(df_comp)

            ind_data = self._get_indicator_data(df_comp)

            comp_data.update(dict(name=comp, fm=fm_data, indicator=ind_data))

            comps_data.update({comp: comp_data})

        return comps_data

    def _get_indicator_data(self, df_comp):

        df_ind = (
            df_comp["indicator_model"]["indicator"].dropna(how="all").set_index("name")
        )
        df_ind["name"] = df_ind.index
        ind_data = df_ind.to_dict("index")

        return ind_data

    def _get_failure_mode_data(self, df_comp):

        fms_data = dict()
        fm_key = ("failure_model", "failure_mode", "name")
        failure_modes = df_comp[fm_key].unique()
        df_fms = df_comp[
            [
                "failure_model",
                "condition_model",
                "task_model",
                "trigger_model",
                "impact_model",
            ]
        ].set_index(fm_key)

        for fm in failure_modes:

            df_fm = df_fms.loc[[fm]]

            fm_data = (
                df_fm["failure_model"]["failure_mode"]
                .dropna(how="all")
                .iloc[0]
                .to_dict()
            )

            # Get the Task information
            tasks_data = self._get_task_data(df_fm)

            # Get the Consequence information
            cons_data = self._get_cons_data(df_fm)

            # Get the Distribution information
            dist_data = self._get_dist_data(df_fm)

            # Get the Condition information
            condition_data = self._get_condition_data(df_fm)

            fm_data.update(
                dict(
                    name=fm,
                    conditions=condition_data,
                    tasks=tasks_data,
                    untreated=dist_data,
                    consequence=cons_data,
                )
            )
            fms_data.update(
                {
                    fm: fm_data,
                }
            )

        return fms_data

    def _get_condition_data(self, df_fm):
        # TODO update for new arrangement
        df_cond = (
            df_fm["condition_model"]["condition"].dropna(how="all").set_index("name")
        )
        df_cond["name"] = df_cond.index

        cond_data = df_cond.to_dict("index")

        return cond_data

    def _get_cons_data(self, df_fm):

        df_cons = df_fm["failure_model"].dropna(how="all")
        df_cons = df_cons["consequence"]
        df_cons["name"] = df_cons.index
        try:
            cons_data = df_cons.iloc[0].to_dict()
        except IndexError:
            cons_data = df_cons.to_dict()

        return cons_data

    def _get_dist_data(self, df_fm):

        df_dist = df_fm["failure_model"].dropna(how="all")
        df_dist = df_dist["distribution"]
        df_dist["name"] = df_dist.index
        try:
            dist_data = df_dist.iloc[0].to_dict()
        except IndexError:
            dist_data = df_dist.to_dict()

        return dist_data

    def _get_task_data(self, df_fm):
        """Takes a dataframe for a failure mode and returns a dict of task data"""
        tasks_data = dict()
        task_key = ("task_model", "task", "name")
        tasks = df_fm[task_key].unique()
        df_tasks = df_fm[["task_model", "trigger_model", "impact_model"]].set_index(
            task_key
        )

        for task in tasks:

            df_task = df_tasks.loc[[task]].dropna(axis=0, how="all")

            # Trigger information
            try:
                state = df_task["trigger_model"]["state"].iloc[0].dropna().to_dict()
            except:
                state = df_task["trigger_model"]["state"].dropna().to_dict()

            trigger_data = dict(
                state=state,
                condition=df_task["trigger_model"]["condition"]
                .dropna()
                .set_index("name")
                .to_dict("index"),
            )

            # Impact information
            try:
                state = df_task["impact_model"]["state"].iloc[0].dropna().to_dict()
            except:
                state = df_task["impact_model"]["state"].dropna().to_dict()

            # TODO revist how system impact is set
            system = df_task["impact_model"]["system"]["level"].iloc[0]

            impact_data = dict(
                state=state,
                condition=df_task["impact_model"]["condition"]
                .dropna()
                .set_index("name")
                .to_dict("index"),
                system=system,
            )

            # Tasks specific information
            df_tsi = df_task[("task_model")].dropna(how="all").dropna(axis=1)
            df_tsi.columns = df_tsi.columns.droplevel()

            task_data = df_tsi.to_dict("index")  # TODO currently has too many vars
            try:
                task_data[task].update(
                    dict(
                        name=task,
                        triggers=trigger_data,
                        impacts=impact_data,
                    )
                )
            except:
                task_data = dict(
                    task=dict(
                        name=task,
                        triggers=trigger_data,
                        impacts=impact_data,
                    )
                )

            tasks_data.update(task_data)

        return tasks_data

        # ******************* Validate Methods ***********************

        def validate(self):

            # Check components have a failure mode

            # Check all failure modes have a distribution

            NotImplemented

        def validate_component_has_failure_mode(self):

            NotImplemented