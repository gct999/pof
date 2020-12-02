"""

"""

import pandas as pd
import numpy as np

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pof import Component, FailureMode


def get_color_map(df, column, colour_scheme=None):

    if colour_scheme == "plotly":
        colors = px.colors.qualitative.Plotly
    elif colour_scheme == "bold":
        colors = px.colors.qualitative.Bold
    else:
        colors = px.colors.qualitative.Safe

    color_map = dict(zip(df[column].unique(), colors))

    return color_map


def update_cost_fig(local):
    try:
        df = local.expected_risk_cost_df()

        color_map = get_color_map(df=df, column="task", colour_scheme="bold")

        df = df[df["fm_active"] == True]
        df = df[df["task_active"] == True]

        # Make columns presentable
        df.columns = df.columns.str.replace("_", " ").str.title()
        col_names = {"Time": f"Age ({local.units})"}
        df.rename(columns=col_names, inplace=True)

        px_args = dict(
            data_frame=df,
            x=col_names["Time"],
            y="Cost Cumulative",
            color="Task",
            color_discrete_map=color_map,
            title="Maintenance Strategy Costs",
        )

        if isinstance(local, Component):
            fig = px.area(**px_args, line_group="Failure Mode")
        elif isinstance(local, FailureMode):
            fig = px.area(**px_args)
        else:
            raise TypeError("local must be Component of FailureMode")

        col_names = {"time": f"Age ({local.units})"}

        fig.update_yaxes(automargin=True)
        fig.update_xaxes(automargin=True)
        fig.update_layout(
            legend_traceorder="reversed",
        )
        fig.update_xaxes(title_text=col_names["time"])

    except:
        fig = go.Figure(
            layout=go.Layout(
                title=go.layout.Title(text="Error Producing Maintenance Strategy Costs")
            )
        )
    return fig


def update_pof_fig(local):

    try:
        pof = dict(
            maint=pd.DataFrame(local.expected_pof(t_end=200)),
            no_maint=pd.DataFrame(local.expected_untreated(t_end=200)),
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

        df_active = df[df["key"] == "fm_active"]
        df_active = pd.melt(
            df_active, id_vars=["strategy"], value_vars=df_active.columns[2:]
        ).rename(columns={"variable": "source", "value": "fm_active"})

        df_time = df[df["key"] == "time"]
        df_time = pd.melt(
            df_time, id_vars=["strategy"], value_vars=df_time.columns[2:]
        ).rename(columns={"variable": "source", "value": "time"})
        df_time = df_time.explode("time", ignore_index=True)["time"]

        df = df_pof.merge(df_active, on=["strategy", "source"])
        df["time"] = df_time

        color_map = get_color_map(df=df, column="source", colour_scheme="plotly")

        df = df[df["fm_active"] == True]

        # Make columns presentable
        # df.columns = df.columns.str.replace("_", " ").str.title()
        col_names = {"time": f"Age ({local.units})"}
        df.rename(columns=col_names, inplace=True)

        fig = px.line(
            df,
            x=col_names["time"],
            y="pof",
            color="source",
            color_discrete_map=color_map,
            line_dash="strategy",
            line_group="strategy",
            title="Probability of Failure given Maintenance Strategy",
        )

        col_names = {"time": f"Age ({local.units})"}

        fig.layout.yaxis.tickformat = ",.0%"
        fig.update_yaxes(automargin=True)
        fig.update_xaxes(automargin=True)
        fig.update_xaxes(title_text=col_names["time"])
    except:
        fig = go.Figure(
            layout=go.Layout(
                title=go.layout.Title(text="Error Producing Probability of Failure")
            )
        )

    return fig


def update_condition_fig(local, conf=0.95):
    """ Updates the condition figure"""

    try:

        ecl = local.expected_condition()

        subplot_titles = [x.replace("_", " ").title() for x in list(ecl.keys())]

        fig = make_subplots(
            rows=len(ecl),
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=subplot_titles,
        )

        cmap = px.colors.qualitative.Safe
        idx = 1

        for cond_name, cond in ecl.items():
            # Format the data for plotting
            length = len(cond["mean"])
            time = np.linspace(
                0, length - 1, length, dtype=int
            )  # TODO take time as a variable
            x = np.append(time, time[::-1])
            y = np.append(cond["upper"], cond["lower"][::-1])

            # Add the boundary
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    fill="toself",
                    fillcolor="rgba" + cmap[idx][3:-2] + ",0.2)",
                    line_color="rgba(255,255,255,0)",
                    showlegend=False,
                    name=cond_name,
                ),
                row=idx,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=cond["mean"],
                    line_color=cmap[idx],
                    name=cond_name,
                    showlegend=False,
                ),
                row=idx,
                col=1,
            )
            fig.update_yaxes(
                title_text="".join(
                    [x[0] for x in cond_name.replace("_", " ").title().split(" ")]
                )
                + " Measure",
                row=idx,
                automargin=True,
            )
            idx = idx + 1

        col_names = {"time": f"Age ({local.units})"}

        fig.update_traces(mode="lines")
        fig.update_xaxes(
            title_text=col_names["time"],
            row=len(ecl),
            automargin=True,
        )
        fig.update_layout(
            title="Expected Condition (Confidence = " + f"{conf}" + ")",
            legend_traceorder="normal",
        )

    except:
        fig = go.Figure(
            layout=go.Layout(title=go.layout.Title(text="Error Producing Condition"))
        )

    return fig


def make_sensitivity_fig(
    local, var_name="", lower=0, upper=10, step_size=1, n_iterations=10
):

    var = var_name.split("-")[-1]
    y_axis = "annual_cost"

    title_var = var.replace("_", " ").title()

    try:
        df = local.expected_sensitivity(
            var_name=var_name,
            lower=lower,
            upper=upper,
            step_size=step_size,
            n_iterations=n_iterations,
        )

        # Add direct and indirect
        df_total = df.groupby(by=[var]).sum()
        df_direct = df_total - df.loc[df["source"] == "risk"].groupby(by=[var]).sum()
        summary = {
            "total": df_total,
            "direct": df_direct,
            "risk": df.loc[df["source"] == "risk"],
        }

        df_plot = pd.concat(summary, names=["source"]).reset_index()
        df_plot["active"] = df_plot["active"].astype(bool)
        df_plot = df_plot.append(df.loc[df["source"] != "risk"])

        # Add line dashes
        df_plot["line_dash"] = 1
        df_plot.loc[
            df_plot["source"].isin(["risk", "direct", "total"]), "line_dash"
        ] = 0

        # Add the colours
        color_map = get_color_map(df=df_plot, column="source")
        df_plot = df_plot.loc[df_plot["active"]]

        fig = px.line(
            df_plot,
            x=var,
            y=y_axis,
            color="source",
            color_discrete_map=color_map,
            line_dash="line_dash",
            title=f"Sensitivity of Risk/Cost to {title_var}",
        )

        fig.update_yaxes(automargin=True)

        fig.update_xaxes(automargin=True)

    except Exception as error:
        raise error
        fig = go.Figure(
            layout=go.Layout(title=go.layout.Title(text=f"Error Producing {title_var}"))
        )

    return fig


def humanise(data):
    # Not used
    if isinstance(pd.DataFrame):
        data.columns = data.columns.str.replace("_", " ").str.title()
        data
    elif isinstance(str):
        data = data.replace("_", " ").title()
