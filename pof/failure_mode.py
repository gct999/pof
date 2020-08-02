"""

Author: Gavin Treseder
"""

# ************ Packages ********************
import numpy as np
import pandas as pd
import scipy.stats as ss
from scipy.linalg import circulant
from matplotlib import pyplot as plt
from random import random, seed

from pof.condition import Condition
from pof.distribution import Distribution
from pof.consequence import Consequence
from pof.task import Inspection, OnConditionRestoration, Replace

#TODO move t somewhere else
#TODO create better constructors https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-have-multiple-constructors-in-python

seed(1)

class FailureMode: #Maybe rename to failure mode

    def __init__(self, alpha, beta, gamma, scenario='test'):

        # Failure behaviour
        self.failure_dist = None
        self.init_dist = None

        # Set the time period of interested # TODO Make this an input
        self.t = np.arange(0,101,1)

        self.pf_interval = 5 #TODO

        self.conditions = dict()

        # Failure information
        self.t_fm = 0
        self.t_uptime = 0
        self.t_downtime = 0
        self.cof = Consequence() #TODO change to a consequence model
        self.pof = None #TODO

        # Failre Mode state
        self.states = dict()
        self._initiated = False
        self._detected = False
        self._failed = False

        #TODO maybe turn this into a class

        self.t_initiated = False #TODO

        # Tasks
        self.task_order = [1,2,3,4] # 'inspect', 'replace', repair' # todo
        
        self.tasks = dict()

        #self.inspection = Inspection(trigger='time')
        self.corrective_maintenance = Replace()

        # Prepare the failure mode
        #self.calc_init_dist() TODO make this method based on a flag

        # kpis? #TODO
        # Cost and Value of current task? #TODO
        self.value = None #TODO

        if scenario == 'test':
            self.set_test()

        return
    
    # ************** Set Functions *****************

    def set_test(self):

        self.set_failure_dist(
            Distribution(alpha=50, beta=1.5, gamma=10)
        )

        self.set_conditions(dict(
            wall_thickness = Condition(100, 0, 'linear', [-5], name = 'wall_thickness'),
            external_diameter = Condition(100, 0, 'linear', [-2], name = 'external_diameter'),
        ))

        self.set_tasks(dict(
            inspection = Inspection(trigger = 'time'), 
            ocr = OnConditionRestoration(trigger = 'condition'),
            
        ))

        self.set_states(dict(
            initiation = False,
            detection = False,
            failure = False,
        ))

        # Prepare the failure mode
        self.calc_init_dist()
    
        return True

    def set_failure_dist(self, failure_dist):
        self.failure_dist = failure_dist

    def set_tasks(self, tasks):
        """
        Takes a dictionary of tasks and sets the failure mode tasks
        """

        for task_name, task in tasks.items():
            self.tasks[task_name] = task

        return True

    def set_states(self, states):

        for state_name, state in states.items():
            self.states[state_name] = state
        
        return True

    def set_conditions(self, conditions):
        """
        Takes a dictionary of conditions and sets the failure mode conditions
        """

        for cond_name, condition in conditions.items():
            self.conditions[cond_name] = condition

        return True

    # ************** Get Functions *****************

    def get_states(self):

        states = dict(
            initiation = self._initiated,
            failure = self._failed,
            detection = self._detected,
        )
    
        return states

    # ************** Is Function *******************

    def is_failed(self):
        return self.states['failure']

    def is_initiated(self):
        return self.states['initiation']

    def is_detected(self):
        return self.states['detection']

    # ******

    def calc_init_dist(self): #TODO needs to get passed a condition and a pof
        """
        Convert the probability of failure into a probability of initiation
        """

        # Super simple placeholder # TODO add other methods
        alpha = self.failure_dist.alpha
        beta = self.failure_dist.beta
        gamma = self.failure_dist.gamma - self.pf_interval

        self.init_dist = Distribution(alpha=alpha, beta=beta, gamma=gamma)

        return


    def get_expected_condition(self, t_min, t_max): #TODO retire?
        
        t_forecast = np.linspace(t_min, t_max, t_max-t_min+1, dtype = int)

        # Calculate the probability of initiation for the time period 
        prob_initiation = f_ti[t_forecast[1:]]

        # Add the probability after t_max onto the final row with perfect condition
        prob_not_considered = sf_i[t_max]
        prob_initiation = np.append(
            prob_initiation,
            prob_not_considered
        )

        # Scale to ignore the probability that occurs before t_min
        prob_initiation = prob_initiation / prob_initiation.sum()

        # Create a condition matrix of future condition
        deg_matrix = np.tril(np.full((deg_curve.size, deg_curve.size),100),-1) + np.triu(circulant(deg_curve).T)

        condition_outcomes = (deg_matrix.T * prob_initiation).T
        
        condition_mean = condition_outcomes.sum(axis=0)

        return True


        # Need to consider condition that has a probability of outcomes ()


    # *************** Condition Loss *************** # TODO not updated to new method

    def measure_condition_loss(self):

        return self.condition.measure()

    def get_cond_loss(self):

        # New Condition at end of t

        return
    
    def get_p_initiation(self, t_step): #TODO make a robust time step. (t_min, t_max, etc)

        if self._initiated == True:
            p_i = 1
        else:
            p_i = self.init_dist.conditional_f(self.t_fm, self.t_fm + t_step) #TODO update to actual time

        return p_i
    
    
    def sim_event (self):

        # Find first task to be actioned

        # Complete task triggers

        # Refresh the timeline where maintenance or intervention

        # Increment maint

        return NotImplemented

    # ****************** Timeline ******************

    def sim_timeline(self, t_end, t_start=0):
        """
        Simulates a single timeline to determine the state, condition and tasks
        """
        timeline = dict(
            time = np.linspace(t_start, t_end, t_end-t_start + 1, dtype=int)
        )

        # Get intiaition
        timeline['initiation'] = np.full(t_end + 1, self._initiated)
        t_initiate = 0
        if not self._initiated:
            t_initiate = min(t_end, int(self.init_dist.sample()))
            timeline['initiation'][t_initiate:] = 1

        # Get condtiion
        for condition in self.conditions.values(): 
            timeline[condition.name] = condition.get_condition_profile(t_start=-t_initiate, t_stop=t_end - t_initiate)

        # Check tasks with time based trigger
        for task in self.tasks.values():

            if task.trigger == 'time': 
                timeline[task.activity] = task.sim_timeline(t_end)

        # Check detection
        if self._detected:
            timeline['detection'] = np.full(t_end + 1, True)
        else:
            timeline['detection'] = self.tasks['inspection'].sim_completion(t_end, timeline)['detection'] # TODO update this

        # Check failure
        timeline['failure'] = np.full(t_end + 1, self._failed)
        if not self._failed:
            for condition in self.conditions.values():
                tl_f = condition.sim_failure_timeline(t_start = - t_initiate, t_stop = t_end - t_initiate)
                timeline['failure'] = (timeline['failure']) | (tl_f)

        # Check tasks with condition based trigger
        for task in self.tasks.values():

            if task.trigger == 'condition':
                timeline[task.name] = task.sim_timeline(t_end, timeline)

        self.timeline = timeline

        return timeline
    
    def init_timeline(self, t_end, t_start = 0):

        # Initiate times
        # 
        return NotImplemented


    def thought_process(self):

        # Init timeline

        # Get next_task

        # While still tasks before t_end

            # Execute Task

            # Update timeline for things that need updating ()

            # Get next task

        return NotImplemented

    def update_timeline_2(self):

        #if state, update state

        #if 
        return NotImplemented

    def update_timeline(self, t_end, t_start=0, conditions_to_update = dict(), states_to_update = dict(), reset_tasks = False):
        """
        Takes a timeline and updates tasks that are impacted
        """
        # Initiation -> Condition -> time_tasks -> states -> tasks
        
        timeline = self.timeline 
        # Check for initiation changes
        if 'intiation' in states_to_update:
            timeline['initiation'][t_start:t_end] = np.full(t_end - t_start + 1, states_to_update['initiation'])
            t_initiate = t_start
            if states_to_update['initiation'] == False:
                t_initiate = min(t_end, int(self.init_dist.sample()))
                timeline['initiation'][t_initiate:] = 1

        # Check for condition changes
        for condition in self.conditions.values():
            if condition.name in conditions_to_update:
                timeline[condition.name][t_start:t_end] = condition.get_condition_profile(t_start=-t_initiate, t_stop=t_end - t_initiate)

        # Check for detection changes
        if 'detection' in states_to_update:
            timeline['detection'][t_start:t_end] = np.full(t_end - t_start + 1, states_to_update['detection'])

        # Check for failure changes
        if 'failure' in states_to_update:
            timeline['failure'] = np.full(t_end - t_start + 1, states_to_update['failed'])
            if states_to_update['failed'] == False:
                for condition in self.conditions.values():
                    tl_f = condition.sim_failure_timeline(t_start = - t_initiate, t_stop = t_end - t_initiate)
                    timeline['failure'] = (timeline['failure']) | (tl_f)

        # Check tasks with time based trigger #TODO Add variable for checking if time based tasks are reset?
        """for task in self.tasks.values():
    
            if task.trigger == 'time' and task.name in tasks_to_update: 
                timeline[task.name] = task.sim_timeline(s_tart=t_start, t_end=t_end)

        # Check tasks with condition based trigger
        for task in self.tasks.values():

            if task.trigger == 'condition' and task.name in tasks_to_update:
                timeline[task.name] = task.sim_timeline(t_start=t_start, t_end=t_end, timeline=timeline)"""

        self.timeline = timeline

        return timeline


    def next_tasks(self, timeline, t_start = 0, t_end = None):
        """
        Takes a timeline and returns the next time, and next task that will be completed
        """
        if t_end is None:
            t_end = timeline['time'][-1]

        next_tasks = []
        next_time = t_end

        for task in self.tasks: # TODO make this more efficient by using a task array rather than a for loop

            if 0 in timeline[task][t_start:t_end]:
                t_task = timeline['time'][np.argmax(timeline[task][t_start:]==0)] + t_start

                if t_task < next_time:
                    next_tasks = [task]
                    next_time = t_task
                elif t_task == next_time:
                    next_tasks = np.append(next_tasks, task)

        return next_time, next_tasks

    def simulate(self, t_end = 100):

        t_now = 0

        while t_now < t_end:

            timeline = self.sim_timeline(t_start=t_now, t_end=t_end)
            t_now, tasks = self.next_tasks(timeline, t_end)

            for task in tasks:

                # Execute the task
                states, conditions = self.tasks[task].sim_completion()

            

                # TODO replaced this with a loop to only update the ones that have changed.

    # ****************** Simple outputs  ************

    def plot_timeline(self):

        fig, (ax_state, ax_cond, ax_task) = plt.subplots(1, 3)

        fig.set_figheight (4)
        fig.set_figwidth (24)

        ax_cond.set_title('Condition')
        ax_state.set_title('State')
        ax_task.set_title('Task')
        
        for condition in self.conditions:
            ax_cond.plot(self.timeline['time'], self.timeline[condition])

        for state in self.get_states():
            ax_state.plot(self.timeline['time'], self.timeline[state])

        for task in self.tasks:
            ax_task.plot(self.timeline['time'], self.timeline[task])

        plt.show()

    # ****************** Simulate *******************

    def sim(self, t_step):

        # Check for initiation
        self.sim_initiation(t_step)

        # Check for condition
        if self._initiated:

            self.sim_condition(t_step) # TODO check for all condition for loop

            # Check for failure
            self.sim_failure(t_step)

            if self._failed:
                
                #Trigger corrective Maintenance
                self.sim_corrective_maintenance(t_step)

        # Check for detection TODO is this just a task
        self.sim_detection(t_step)

        # Check for tasks
            # Replace
            # Repair 

        # Increment time
        self.t_fm = self.t_fm + t_step

        # Record History
        self.record_history()

        return

    def sim_initiation(self, t_step):

        if self._initiated == False:

            p_i = self.get_p_initiation(t_step = t_step)
            
            if(random() < p_i):

                self._initiated = True
                self.t_initiated = self.t_fm

        return

    def sim_condition(self, t_step):

        # Simple method -> increment the condition
        return self.condition.sim(t_step)

    def sim_failure(self, t_step): #TODO failure doesn't need time

        # TODO add for loop and check all methods
        self._failed = self.condition.is_failed() #TODO or sytmpom or safety factor failure?

        return self._failed

    def sim_detection(self, t_step):

        det = self.inspection.sim_inspect(t_step, self.condition)

        if det == True:
            self._detected = True
          
    def sim_corrective_maintenance (self, t_step):
        """
        Currently stubbed as a replace task #TODO
        """
        # Complete the corrective maintenace task
        #if self.corrective_maintenance.is_triggered(self):
            


        return NotImplemented

    def sim_tasks(self, t_step):

        # Check time triggers, check condition triggers

        
        # Check time triggers
        for task in self.tasks:

            if task.trigger_type == 'time':
                
                # Check if the time has been triggered
                task.check_time(self.t_fm + t_step)



        # Check on condition triggers
        for task in self.tasks:
            
            task.check_trigger(self.t_fm + t_step)

        # Check value? trigger
        return NotImplemented


    def sim_history(self):

        nrows = len(self._history)
        fig, ax = plt.subplots(nrows=5, ncols=1)

        row = 0

        for field in  ["_initiated", "_detected", '_failed']:
            ax[row].step(self._history['t_fm'], self._history[field])
            ax[row].set_ylabel(field)
            
            row = row + 1

        for field in  ['condition']:
            ax[row].plot(self._history['t_fm'], self._history[field])
            ax[row].set_ylabel(field)
            
            row = row + 1

    # ****************** Optimise routines ***********

    def optimal_strategy(self):
        """
        Ouptut - Run To Failure, Scheduled Replacement, Scheduled Repair, On Condition Replacement, On Condition Replacement
        """

        # For each increment

            # For each simulation

                # Record outputs

                # Cost
                # Consequence
                # Reliability
                    # n_failures
                # Availability
                    # Uptime
                    # Downtime

        # Plot outputs

        # Return optimal strategy
