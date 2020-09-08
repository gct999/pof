import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

#from settings import Settings

IS_OPEN = False

# Asset

    
    # Components

        # Condition

        # Task Groups ( move to assets)

        # Failure Modes

            # Failure Distribution

            # Condition (Loss)
            
            # Tasks

            # Tasks
                # Params
                    # Probability Effective
                    # Cost
                    # Consequence

                # Trigger
                    # Time TODO
                    # State (n)
                        # state_name
                        # state (True/False)
                    # Conditions (n)
                        # condition_name
                        # lower_threshold
                        # upper_threshold
                # Impacts
                    # Time TODO
                    # States (n)
                        # state_name
                        # state (True / False)
                    # Conditions (n)
                        # condition_name
                        # method
                        # axis
                        # reduction_factor / target

# ******************* Component ******************

def make_component_layout(component, prefix="", sep='-'):
    """
    """
    
    # Get tasks layout
    fms_layout = []
    for fm_name, fm in component.fm.items():
        fm_prefix = prefix + 'failure_mode' + sep + fm_name + sep
        fms_layout = fms_layout + [make_failure_mode_layout(fm, fm_name, prefix=fm_prefix, sep=sep)]

    # Make the layout
    layout = dbc.InputGroup(
        [
            dbc.InputGroupAddon(dbc.Checkbox(id=prefix + 'active', checked=True), addon_type="prepend"),

            dbc.Button(
                component.name,
                color="link",
                id = prefix + "collapse-button",
            ),
            dbc.Col(
                [
                    dbc.Collapse(
                        dbc.Card(dbc.CardBody(
                                fms_layout
                        )),
                        id = prefix + "collapse",
                        is_open=IS_OPEN
                    ),
                ]
            )

        ]
    )

    return layout


def make_failure_mode_layout(failure_mode, fm_name, prefix="", sep='-'):
    """
    """
    
    # Get failure mode form
    fd_prefix = prefix + "failure_dist" + sep
    dist_layout = make_dist_layout(failure_mode.failure_dist, prefix=fd_prefix, sep=sep)

    # Get tasks layout
    tasks_layout = []
    for task_name, task in failure_mode.tasks.items():
        task_prefix = prefix + 'task' + sep + task_name + sep
        tasks_layout = tasks_layout + [make_task_layout(task, task_name, prefix=task_prefix, sep=sep)]

    # Make the layout
    layout = dbc.InputGroup(
        [
            dbc.InputGroupAddon(dbc.Checkbox(id=prefix + 'active', checked=True), addon_type="prepend"),

            dbc.Button(
                fm_name,
                color="link",
                id = prefix + "collapse-button",
            ),
            dbc.Col(
                [
                    dist_layout,
                    dbc.Collapse(
                        dbc.Card(dbc.CardBody(
                                tasks_layout
                        )),
                        id = prefix + "collapse",
                        is_open=IS_OPEN
                    ),
                ]
            )

        ]
    )

    return layout

def make_dist_layout(dist, prefix="", sep='-'):
    """
    Takes a Distribution and generates the html form inputs
    """
    param_inputs = []

    for param, value in dist.params().items():
        param_input = dbc.Col(
            dbc.FormGroup(
                [
                    dbc.Label(param.capitalize(), className="mr-2"),
                    dbc.Input(
                        type="number",
                        id= prefix + param,
                        value=value,
                        debounce=True,
                    ),
                ],
                className='mr-3',
            ),
        )
        param_inputs.append(param_input)

    form = dbc.Form(children=param_inputs, inline=True)

    return form


def make_task_layout(task, task_name="task", prefix="", sep = '-'):
    """

    """
    task_form = make_task_form(task=task, prefix=prefix)
    trigger_layout = make_task_trigger_layout(task.triggers, prefix=prefix)
    impact_layout = make_task_impact_layout(task.impacts, prefix=prefix)

    task_layout = dbc.InputGroup(
        [
            dbc.InputGroupAddon(dbc.Checkbox(id=prefix + 'active', checked=True), addon_type="prepend"),
            dbc.Button(
                task_name,
                color="link",
                id = prefix + "collapse-button",
            ),
            dbc.Col(
                [
                    task_form,
                    dbc.Collapse(
                        dbc.CardDeck(
                            [
                                trigger_layout,
                                impact_layout,
                            ]
                        ),
                        id = prefix + "collapse",
                        is_open=IS_OPEN
                    ),
                ]
            )
        ]
    )

    return task_layout

def make_task_form(task, prefix="", sep='-'): #TODO make this better
    """
    Takes a Task and generates the html form inputs
    """

    if task.trigger == 'time':
        time_details = [
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Label("Time Delay"),
                        dbc.Input(
                            type="number",
                            id= prefix + "t_delay",
                            value = task.t_delay,
                            debounce=True,
                        ),
                    ],
                ),
            ),
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Label("Time Interval"),
                        dbc.Input(
                            type="number",
                            id= prefix + "t_interval",
                            value = task.t_interval,
                            debounce=True,
                        ),
                    ],
                ),
            ),
        ]
    else:
        time_details = []

    form = dbc.Form(
        [
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.Label("Prob Effective", html_for="p_effective"),
                        dbc.Input(
                            type="number",
                            id= prefix + "p_effective",
                            value = task.p_effective * 100,
                            debounce=True,
                        ),
                        dbc.InputGroupAddon("%", addon_type="append"),
                    ],
                ),
            ),
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Label("Cost", html_for="cost"),
                        dbc.Input(
                            type="number",
                            id= prefix + "cost",
                            value= task.cost,
                            debounce=True,
                        ),
                    ],
                ),
            ),
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Label("Consequence", html_for="consequence"),
                        dbc.Input(
                            type="number",
                            id= prefix + "consequence",
                            value="Not Implemented",
                            debounce=True,
                        ),
                    ],
                ),
            ),
        ] + time_details,
        inline=True,
    )

    return form

# ******************* Triggers ******************


def make_task_trigger_layout(triggers, prefix="", sep='-'):
    """
    Takes a Trigger and generates the html form inputs
    """
    prefix = prefix + 'trigger' + sep
    state_layout = make_state_impact_layout(triggers['state'], prefix=prefix)
    condition_layout = make_condition_trigger_layout(triggers['condition'], prefix=prefix)

    layout = dbc.Card(
        [
            dbc.CardHeader("Triggers"),
            dbc.CardBody(
                [
                    state_layout,
                    condition_layout,
                ],
            ),
        ],
    )

    return layout


def make_condition_trigger_layout(triggers, prefix="", sep='-'): # TODO make these sliders
    """ R
    """
    condition_inputs = []

    for condition, threshold in triggers.items():
        
        prefix = prefix + 'condition' + sep + condition + sep
        condition_input = dbc.InputGroup(
            [
                dbc.InputGroupAddon(
                    [
                        dbc.Checkbox(id=prefix + 'active', checked=True),
                        
                    ],
                    addon_type="prepend"
                ),
                dbc.Label(condition.capitalize(), className="mr-2"),
                dbc.Form(
                    [
                        dbc.Input(
                            type="number",
                            id= prefix + "lower",
                            value=threshold['lower'],
                            debounce=True,
                        ),
                        dbc.Input(
                            type="number",
                            id= prefix + "upper",
                            value=threshold['upper'],
                            debounce=True,
                        ),
                    ],
                    inline=True
                )
            ]
        )
        condition_inputs = condition_inputs + [condition_input]

    layout = dbc.Form(children=condition_inputs)
    
    return layout


# ****************** Impacts *************************

def make_task_impact_layout(impacts, prefix="", sep='-'):
    """Takes a the impacts from a Trigger object and generates the html form inputs
    # TODO Implement times
    """
    prefix = prefix + 'impact' + sep
    state_layout = make_state_impact_layout(impacts['state'], prefix=prefix)
    condition_layout = make_condition_impact_layout(impacts['condition'], prefix=prefix)

    layout = dbc.Card(
        [
            dbc.CardHeader("Impacts"),
            dbc.CardBody(
                [
                    state_layout,
                    condition_layout,
                ],
            ),
        ],
    )

    return layout

def make_state_impact_layout(state_impacts, prefix="", sep='-'):
    """ Creates an input form the state impacts
    """

    #TODO figure out how to take True or False as vlaues
    state_inputs = []
    prefix = prefix + 'state' + sep
    for state, value in state_impacts.items():
        state_input = dbc.Col(
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon(
                        [
                            dbc.Checkbox(
                                id=prefix + state + sep + 'active',
                                checked=True),
                            dbc.Label(state.capitalize(), className="mr-2"),
                        ],
                        addon_type="prepend"),
                    dbc.Select(
                        options=[{'label' : option, 'value' : option} for option in ["True", "False"]],
                        id= prefix + state,
                        value=str(value),
                    ),
                ],
                className='mr-3',
            ),
        )
        state_inputs = state_inputs + [state_input]

    form = dbc.Form(children=state_inputs, inline=True)

    return form

def make_condition_impact_layout(impacts, prefix="", sep= '-'):

    forms = []
    base_prefix = prefix
    for condition, impact in impacts.items():
        prefix = base_prefix + 'condition' + sep + condition + sep

        condition_form = dbc.InputGroup(
            [
                dbc.InputGroupAddon(dbc.Checkbox(id=prefix + 'active', checked=True), addon_type="prepend"),
                dbc.InputGroupAddon(condition, addon_type="prepend"),
                make_condition_impact_form(impact, prefix=prefix),
            ]
        )
        
        forms = forms + [condition_form]

    layout = dbc.Form(forms)

    return layout

def make_condition_impact_form(impact, prefix="", sep='-'):
    """Create a form for impact condition with method, axis and target
    """

    target = dbc.FormGroup(
        [
            dbc.Label("Target", className="mr-2"),
            dbc.Input(
                type="number",
                id= prefix + "target",
                value=impact['target'],
                debounce=True,
            ),
        ],
        className="mr-3",
    )

    method = dbc.FormGroup(
        [
            dbc.Label("Method", className="mr-2"),
            dbc.Select(
                id=prefix + "method",
                options=[{'label' : method, 'value' : method} for method in ['reduction_factor', 'tbc']],
                value=impact['method'],
            ),
        ],
        className="mr-3",
    )

    axis = dbc.FormGroup(
        [
            dbc.Label("Axis", className="mr-2"),
            dbc.Select(
                id=prefix + "axis",
                options=[{'label' : axis, 'value' : axis} for axis in ['condition', 'time']],
                value=impact['axis'],
            ),
        ],
        className="mr-3",
    )

    form = dbc.Form([target, method, axis], inline=True, className="dash-bootstrap")

    return form



if __name__ == "__main__":
    print("layout methods - Ok")