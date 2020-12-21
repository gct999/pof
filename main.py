import copy
import os
import logging

import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from config import config
from pof import Component
from pof.units import valid_units
from pof.loader.asset_model_loader import AssetModelLoader
from pof.interface.dashlogger import DashLogger
from pof.interface.layouts import (
    make_layout,
    cf,
    scale_input,
)

# TODO fix the need to import cf

from pof.data.asset_data import SimpleFleet

# Forecast years
START_YEAR = 2015
END_YEAR = 2024
CURRENT_YEAR = 2020

# Population Data
file_path = os.path.dirname(os.path.dirname(__file__)) + r"\inputs" + os.sep
FILE_NAME = r"population_summary.csv"

sfd = SimpleFleet(file_path + FILE_NAME)
sfd.load()
sfd.calc_forecast_age(START_YEAR, END_YEAR, CURRENT_YEAR)

# Asset Model Data
file_path = os.getcwd() + r"\data\inputs" + os.sep
FILE_NAME = r"Asset Model - Pole - Timber.xlsx"

aml = AssetModelLoader(file_path + FILE_NAME)
comp_data = aml.load()
comp = Component.from_dict(comp_data["pole"])
comp.fleet_data = sfd  # TODO fix by creating asset class

# Turn off logging level to speed up implementation
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Build App
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

# Globals
pof_sim = copy.copy(comp)
sens_sim = copy.copy(comp)

# Layout
var_to_scale = cf.scaling
app.layout = make_layout(comp)

# ========================================================
# Collapsable objects to hide information when not needed.
# ========================================================

# Get the dash ids for all the objects that have a collapse button
collapse_ids = comp.get_objects()
collapse_ids.append("sim_params")
collapse_ids.append("indicator_inputs")
collapse_ids.append("consequence_input")


@app.callback(
    [Output(f"{prefix}-collapse", "is_open") for prefix in collapse_ids],
    [Input(f"{prefix}-collapse-button", "n_clicks") for prefix in collapse_ids],
    [State(f"{prefix}-collapse", "is_open") for prefix in collapse_ids],
)
def toggle_collapses(*args):
    """ Expands and collapses hidden dash components in the interface"""
    ctx = dash.callback_context

    state_id = ""
    collapse_id = (
        ctx.triggered[0]["prop_id"].split(".")[0].replace("-collapse-button", "")
    )
    if collapse_id in collapse_ids:  # TODO change to is not None

        state_id = collapse_id + "-collapse.is_open"
        ctx.states[state_id] = not ctx.states[state_id]

    is_open = tuple(ctx.states.values())

    return is_open


sim_triggers = comp.get_dash_ids(numericalOnly=False)
param_inputs = [
    Input(dash_id, "checked") if "active" in dash_id else Input(dash_id, "value")
    for dash_id in sim_triggers
]

# ========================================================
# UPDATE --> Simulate --> Figures
#        --> Simulate --> Figures
# ========================================================

# TODO make a better unit update


@app.callback(
    Output("update_state", "children"),
    Input("input_units-dropdown", "value"),
    Input("model_units-dropdown", "value"),
    param_inputs,
)
def update_parameter(input_units, model_units, *args):
    """Update a the pof object whenever an input is changes""",

    # Check the parameters that changed
    ctx = dash.callback_context
    dash_id = None
    value = None

    # If any parameters have changed update the objecte
    if ctx.triggered:
        comp.units = model_units
        comp.graph_units = input_units  # use the input units for graphing
        dash_id = ctx.triggered[0]["prop_id"].split(".")[0]
        value = ctx.triggered[0]["value"]

        # Scale the value if req
        var = dash_id.split("-")[-1]
        value = scale_input(pof_obj=comp, attr=var, value=value, units=input_units)

        # update the model
        comp.update(dash_id, value)

    return f"Update State: {dash_id} - {value}"


@app.callback(
    Output("sim_state", "children"),
    Output("sim_state_err", "children"),
    Input("update_state", "children"),
    Input("sim_n_active", "checked"),
    Input("t_end-input", "value"),
    Input("n_iterations-input", "value"),
    State("input_units-dropdown", "value"),
)
def update_simulation(__, active, t_end, n_iterations, units):
    """ Triger a simulation whenever an update is completed or the number of iterations change"""
    global pof_sim
    global sfd

    pof_sim.cancel_sim()

    # time.sleep(1)
    if active:
        pof_sim = copy.copy(comp)

        # Scale t_end # TODO generalise funciton and move
        t_end = scale_input(pof_sim, "t_end", t_end, units)

        # Complete the simulations
        pof_sim.mp_timeline(t_end=t_end, n_iterations=n_iterations)

        # Produce reports
        pof_sim.expected_risk_cost_df(t_end=t_end)
        pof_sim.calc_pof_df(t_end=t_end)
        pof_sim.calc_df_task_forecast(sfd)
        pof_sim.calc_df_cond()

        if not pof_sim.up_to_date:
            return dash.no_update, f"Update cancelled"

    else:
        return dash.no_update, "Not active"

    return f"Sim State: {pof_sim.n_iterations} - {n_iterations}", ""


@app.callback(
    Output("cond-fig", "figure"),
    Output("ms-fig", "figure"),
    Output("pof-fig", "figure"),
    Output("task_forecast-fig", "figure"),
    # Output("pop_table-fig", "figure"),
    Output("forecast_table-fig", "figure"),
    Input("sim_state", "children"),
    Input("ms_var_y-dropdown", "value"),
    Input("t_end-input", "value"),
    Input("axis_lock-checkbox", "checked"),
    State("sim_n_active", "checked"),
    State("cond-fig", "figure"),
    State("ms-fig", "figure"),
    State("pof-fig", "figure"),
    State("task_forecast-fig", "figure"),
)
def update_figures(
    state,
    y_axis,
    t_end,
    active,
    axis_lock,
    prev_cond_fig,
    prev_ms_fig,
    prev_pof_fig,
    prev_task_fig,
    *args,
):
    global pof_sim
    global sfd

    if active:

        ctx = dash.callback_context
        dash_id = ctx.triggered[0]["prop_id"].split(".")[0]
        keep_axis = dash_id == "sim_state" and axis_lock

        pof_fig = pof_sim.plot_pof(keep_axis=keep_axis, prev=prev_pof_fig)

        ms_fig = pof_sim.plot_ms(y_axis=y_axis, keep_axis=keep_axis, prev=prev_ms_fig)

        cond_fig = pof_sim.plot_cond(keep_axis=keep_axis, prev=prev_cond_fig)

        task_forecast_fig = pof_sim.plot_task_forecast(
            keep_axis=keep_axis, prev=prev_task_fig
        )

        # pop_table_fig = pof_sim.plot_pop_table()

        forecast_table_fig = pof_sim.plot_summary(sfd.df_age)

    else:
        raise PreventUpdate

    return (
        cond_fig,
        ms_fig,
        pof_fig,
        task_forecast_fig,
        # pop_table_fig,
        forecast_table_fig,
    )


@app.callback(Output("ffcf", "children"), [Input("sim_state", "children")])
def update_ffcf(*args):
    """ Returns the ratio between conditional failures, functional failures and in service assets"""
    n_cf = len(pof_sim.expected_cf())
    n_ff = len(pof_sim.expected_ff())

    try:
        ratio = round(n_ff / (n_cf + n_ff), 2)
    except:
        ratio = "--.--"

    return f"Conditional {n_cf} : {n_ff} Functional. {ratio}%"


@app.callback(
    Output("sensitivity-fig", "figure"),
    Input("sim_sens_active-check", "checked"),
    Input("n_sens_iterations-input", "value"),
    Input("sens_var_id-dropdown", "value"),
    Input("sens_var_y-dropdown", "value"),
    Input("sens_lower-input", "value"),
    Input("sens_upper-input", "value"),
    Input("sens_step_size-input", "value"),
    Input("t_end-input", "value"),
    Input("axis_lock-checkbox", "checked"),
    # Input("ms-fig", "figure"),  # TODO change this trigger
    State("sensitivity-fig", "figure"),
    State("input_units-dropdown", "value"),
)
def update_sensitivity(
    active,
    n_iterations,
    var_id,
    y_axis,
    lower,
    upper,
    step_size,
    t_end,
    axis_lock,
    prev_sens,
    units,
    *args,
):
    """ Trigger a sensitivity analysis of the target variable"""
    # Copy from the main model
    global sens_sim
    sens_sim.cancel_sim()

    if active:

        ctx = dash.callback_context
        dash_id = ctx.triggered[0]["prop_id"].split(".")[0]
        keep_axis = dash_id == "sim_state" and axis_lock

        # Scale the inputs if needed
        var = var_id.split("-")[-1]
        lower = scale_input(sens_sim, var, lower, units)
        upper = scale_input(sens_sim, var, upper, units)

        sens_sim = copy.deepcopy(comp)

        sens_sim.expected_sensitivity(
            var_id=var_id,
            lower=lower,
            upper=upper,
            t_end=t_end,
            step_size=step_size,
            n_iterations=n_iterations,
        )

        sens_fig = sens_sim.plot_sens(
            var_id=var_id, y_axis=y_axis, keep_axis=keep_axis, prev=prev_sens
        )

        return sens_fig
    else:
        raise PreventUpdate


# ==============================================
# The following progress bars are always running
# ==============================================


@app.callback(
    Output("n-progress", "value"),
    Output("n-progress", "children"),
    Input("progress-interval", "n_intervals"),
)
def update_progress(n):
    if pof_sim.n is None:
        raise Exception("no process started")
    progress = int(pof_sim.progress() * 100)

    return progress, f"{progress} %" if progress >= 5 else ""


@app.callback(
    [Output("n_sens-progress", "value"), Output("n_sens-progress", "children")],
    [Input("sens_progress-interval", "n_intervals")],
)
def update_progress_sens(n):
    if sens_sim.n is None:
        raise Exception("no process started")
    progress = int(sens_sim.sens_progress() * 100)

    return progress, f"{progress} %" if progress >= 5 else ""


if __name__ == "__main__":
    app.run_server(debug=True)
