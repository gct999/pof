"""
Tests for the FailureMode class
Author: Gavin Treseder
"""

import copy
import unittest
from unittest.mock import Mock, patch

import numpy as np

import fixtures
import testconfig  # pylint: disable=unused-import
from test_pof_base import TestPofBaseCommon
from pof.failure_mode import FailureMode
from pof.task import Task
import pof.demo as demo


def side_effect_trigger_task(**kwargs):
    t_start = kwargs.get("t_start")
    t_end = kwargs.get("t_end")

    return np.full(t_end - t_start + 1, 0)


class TestFailureMode(TestPofBaseCommon, unittest.TestCase):
    def setUp(self):

        super().setUp()

        # TestIntantiate
        self._class = FailureMode

        # TestFromDict
        self._data_valid = [{"name": "TestFailureMode"}]
        self._data_invalid_values = [{"pf_curve": "invalid_value"}]
        self._data_invalid_types = [{"invalid_type": "invalid_type"}]
        self._data_complete = copy.deepcopy(fixtures.complete["failure_mode"])

    def test_inspection_effectiveness(self):

        # Arrange
        task = Mock()
        task.effectiveness = Mock(return_value=0.9)
        task.task_type = "Inspection"

        param_list = [
            ({}, 0),
            ({"insp_1": task}, 0.9),
            ({"insp_1": task, "insp_2": task}, 0.99),
        ]

        for tasks, expected in param_list:

            fm = FailureMode.demo()
            fm.tasks = tasks

            # Act
            actual = fm.inspection_effectiveness()

            # Assert
            self.assertEqual(actual, expected)

    # ************ Test init_timeline ***********************

    def test_init_timeline(self):
        # TODO full coverage

        params = [
            ("step", demo.failure_mode_data["random"]),
            ("linear", demo.failure_mode_data["slow_aging"]),
        ]

        for pf_curve, test_data in params:
            # Arrange
            t_start = 0
            t_end = 200
            fm = FailureMode.load(demo.failure_mode_data["random"])

            # Act
            fm.init_timeline(t_start=0, t_end=200)

            # Check times match
            self.assertEqual(fm.timeline["time"][0], t_start, "t=0 != t_start")
            self.assertEqual(
                fm.timeline["time"][-1],
                t_end,
                "Last time in timeline does not equal t_end",
            )

            # Check states match
            self.assertEqual(
                fm.timeline["initiation"][0],
                fm.is_initiated(),
                "First initiation in timeline does not equal current initiation",
            )
            self.assertEqual(
                fm.timeline["detection"][0],
                fm.is_detected(),
                "First detection in timeline does not equal current detection",
            )
            self.assertEqual(
                fm.timeline["failure"][0],
                fm.is_failed(),
                "First Failure in timeline does not equal current failure",
            )

            # Check conditions match
            # TODO move conditions to indicators first

            # Check tasks match
            # TODO rewrite time function in tasks first

    # ------------ Test update_timeline --------------------
    # TODO robust test for update timelines
    # def test_update_timeline(self):

    #     # Arrange
    #     fm = FailureMode.demo()

    #     fm.update_timeline(t_start=10, updates=dict(initiation=False))

    #     fm.update_timeline(t_start=5, updates=dict(initiation=False))

    # -------------Test sim_timleine ----------------------

    # TODO figure out what this test was meant to target
    # def test_sim_timeline_correct_states(self):

    #     t_init = 1
    #     t_failure = 1

    #     fm = FailureMode.from_dict(fixtures.failure_mode_data["predictable"])

    #     fm.dists["init"].sample = Mock(return_value=[t_init])  # Override failure

    #     fm.sim_timeline(200)

    #     raise NotImplementedError()
    # def test_sim_timeline_on_condition_repair
    def test_sim_timeline_task_on_condition_replacement(self):
        """
        Check an on condition replacement task is triggered when the conditions are met
        """
        task_name = "on_condition_replacement"
        test_data = fixtures.failure_mode_data["slow_aging"]

        param_list = [
            (True, 0, None),
            (False, 0, 2),
        ]

        param_initial = [
            {"indicators": {"slow_degrading": {"initial": 10}}},
            {"indicators": {"fast_degrading": {"initial": 10}}},
            {
                "indicators": {
                    "slow_degrading": {"initial": 10},
                    "fast_degrading": {"initial": 10},
                }
            },
        ]

        for remain_failed, t_task_expected, t_impact_expected in param_list:
            for initial in param_initial:
                with patch.dict(
                    "pof.failure_mode.cf", {"remain_failed": remain_failed}
                ):
                    # Arrange so replacement should occur immediately
                    fm = FailureMode.from_dict(test_data)
                    fm.update_from_dict(initial)
                    fm.reset_for_next_sim()
                    fm.set_states(dict(initiation=True, detection=True))

                    # Act
                    fm.sim_timeline(200)

                    # Assert
                    self.assertEqual(
                        fm.timeline[task_name][t_task_expected],
                        0,
                        f"task should be triggered at t={t_task_expected}",
                    )

                    if not remain_failed:
                        for state, value in (
                            fm.tasks[task_name].impacts["state"].items()
                        ):
                            self.assertEqual(
                                fm.timeline[state][t_impact_expected],
                                value,
                                "impact not completed",
                            )

    def test_sim_timeline_task_on_failure_replacement(self):
        """
        Check that tasks are triggered at the correct time and any impacts occur
        """

        task_name = "on_failure_replacement"
        test_data = {
            "untreated": fixtures.distribution_data["slow_aging"],
            "conditions": {
                "slow_degrading": fixtures.condition_data["slow_degrading"],
                "fast_degrading": fixtures.condition_data["fast_degrading"],
            },
            "tasks": {"replacement": fixtures.replacement_data["on_failure"]},
        }

        # remain_failed, t_task_not_expected, t_task_expected, t_impact_expected
        param_list = [
            (True, 0, 1, None),
            (False, 0, 1, 2),
        ]

        for (
            remain_failed,
            t_task_not_expected,
            t_task_expected,
            t_impact_expected,
        ) in param_list:
            with patch.dict("pof.failure_mode.cf", {"remain_failed": remain_failed}):
                # Arrange
                fm = FailureMode.from_dict(test_data)
                fm.set_states({"initiation": True})
                fm.indicators["slow_degrading"].set_condition(10)
                fm.indicators["fast_degrading"].set_condition(10)

                # Act
                fm.sim_timeline(200)

                # Assert
                self.assertEqual(
                    fm.timeline[task_name][t_task_not_expected],
                    -1,
                    f"task should not be triggered at the t={t_task_not_expected}",
                )
                self.assertEqual(
                    fm.timeline[task_name][t_task_expected],
                    0,
                    f"task should be triggered at t={t_task_expected}",
                )

                if not remain_failed:
                    for state, value in fm.tasks[task_name].impacts["state"].items():
                        self.assertEqual(
                            fm.timeline[state][t_impact_expected],
                            value,
                            "impact not completed",
                        )

    def test_sim_timeline_remain_failed(self):
        """
        Check a timeline is impacted by the 'remain_failed' flag
        """

        params = [(True, 1, 0, False), (False, 2001, 0, True)]
        t_end = 2000

        for remain_failed, time_sim, time_failed, more_tasks in params:

            # Arrange so replacement should occur immediately
            fm = FailureMode.demo()
            fm.indicators["slow_degrading"].set_condition(10)
            fm.indicators["fast_degrading"].set_condition(10)
            fm.set_states(dict(initiation=True, detection=True))

            # Trigger tasks
            fm.dists["init"].sample = Mock(return_value=[0])
            for task in fm.tasks.values():
                task.sim_timeline = Mock(side_effect=side_effect_trigger_task)

            # Act
            with patch.dict("pof.failure_mode.cf", {"remain_failed": remain_failed}):
                fm.sim_timeline(t_end)

                # Assert
                self.assertEqual(len(fm.timeline["time"]), time_sim)
                self.assertEqual(
                    fm.timeline["on_condition_replacement"][0],
                    time_failed,
                    f"task should trigger at t=1",
                )
                for task_name in fm.tasks:
                    self.assertEqual(
                        any(fm.timeline[task_name][1:] + 1),
                        more_tasks,
                        "task should not be triggered again",
                    )

    # ************ Test sim_timeline ***********************

    def test_sim_timeline_condition_step(self):  # TODO full coverage
        t_start = 0
        t_end = 200
        fm = FailureMode.load(demo.failure_mode_data["random"])

        initiation_start = fm.is_initiated()
        detection_start = fm.is_detected()
        failure_start = fm.is_failed()

        fm.sim_timeline(t_start=t_start, t_end=t_end)

        # Check times are ok
        self.assertEqual(
            fm.timeline["time"][0], t_start, "First time does not equal t_start"
        )
        self.assertEqual(
            fm.timeline["time"][-1], t_end, "Last time in timeline does not equal t_end"
        )

        # Check states are ok
        self.assertEqual(
            fm.timeline["initiation"][0],
            initiation_start,
            "First initiation in timeline does not equal current initiation",
        )
        self.assertEqual(
            fm.timeline["initiation"][-1],
            fm.is_initiated(),
            "Last initiation in timeline does not equal current initiation",
        )
        self.assertEqual(
            fm.timeline["detection"][0],
            detection_start,
            "First detection in timeline does not equal current detection",
        )
        self.assertEqual(
            fm.timeline["detection"][-1],
            fm.is_detected(),
            "Last detection in timeline does not equal current detection",
        )
        self.assertEqual(
            fm.timeline["failure"][0],
            failure_start,
            "First Failure in timeline does not equal current failure",
        )
        self.assertEqual(
            fm.timeline["failure"][-1],
            fm.is_failed(),
            "Last Failure in timeline does not equal current failure",
        )

        # Check conditions match
        # TODO move conditions to indicators first

        # Check tasks match
        # TODO rewrite time function in tasks first

    def test_demo(self):
        super().test_demo()

    # ------------ Test mc_timeline ------------------

    def test_mc_timeline(self):

        # Arrange
        fm = FailureMode.demo()

        # Act
        fm.mc_timeline(t_end=20, n_iterations=10)

    def test_mc_timeline_risk_is_accurate(self):
        fm = FailureMode.demo()

        fm.mc_timeline(200)

    # ************ Test get_dash_ids *****************

    def test_get_dash_id(self):

        fm = FailureMode.demo()

        dash_ids = fm.get_dash_ids(numericalOnly=True)

    # ************ Test update methods *****************

    def test_update_invokes_property_method(self):

        # Arrange
        fm1 = FailureMode.demo()
        fm2 = FailureMode.demo()
        test_data = {
            "untreated": {"name": "untreated", "alpha": 20, "beta": 10, "gamma": 5}
        }

        # Act
        fm1.untreated = test_data["untreated"]
        fm2.update(test_data)

        # Assert
        self.assertEquals(fm1, fm2)

    # ************ Test reset methods *****************

    # Change all condition, state and task count. Check values change or don't change for each of them

    # def test_update(self):

    #     test_data_1_fix = fixtures.failure_mode_data["early_life"]
    #     test_data_2_fix = fixtures.failure_mode_data["random"]

    #     fm1 = FailureMode.from_dict(test_data_1_fix)
    #     fm2 = FailureMode.from_dict(test_data_2_fix)

    #     fm1.update_from_dict(test_data_2_fix)

    #     self.assertEqual(fm1, fm2)

    def test_set_task_Task(self):

        fm = FailureMode.from_dict(fixtures.failure_mode_data["random"])

        test_data = Task.from_dict(fixtures.inspection_data["instant"])

        fm.set_obj("tasks", Task, test_data)

        self.assertIsInstance(fm.tasks["inspection"], Task)
        self.assertEqual(
            fm.tasks["inspection"].cost,
            test_data.cost,
        )

    def test_set_task_dict_Task(self):

        fm = FailureMode.from_dict(fixtures.failure_mode_data["random"])

        test_data = dict(inspection=Task.from_dict(fixtures.inspection_data["instant"]))

        fm.set_obj("tasks", Task, test_data)

        self.assertIsInstance(fm.tasks["inspection"], Task)
        self.assertEqual(
            fm.tasks["inspection"].cost,
            test_data["inspection"].cost,
        )

    def test_set_task_dict_update(self):

        fm = FailureMode.from_dict(fixtures.failure_mode_data["random"])

        test_data = dict(inspection=fixtures.inspection_data["instant"])

        fm.set_obj("tasks", Task, test_data)

        self.assertIsInstance(fm.tasks["inspection"], Task)
        self.assertEqual(
            fm.tasks["inspection"].cost,
            test_data["inspection"]["cost"],
        )

    def test_set_task_dict(self):

        fm = FailureMode.from_dict(fixtures.failure_mode_data["random"])

        test_data = fixtures.inspection_data["instant"]

        fm.set_obj("tasks", Task, test_data)

        self.assertIsInstance(fm.tasks["inspection"], Task)
        self.assertEqual(
            fm.tasks["inspection"].cost,
            test_data["cost"],
        )

    # ------------------ Test Expected Risk ------------------------

    # def test_expected_risk(self):

    #     # Arranage
    #     fm = FailureMode.demo()
    #     fm.timeline["failure"] = np.full(0, 200)

    #     # Act
    #     er = fm.expected_risk()

    #     # Assert
    #     np.testing.assert_array_equal(er["time"], [])

    # **************** Test expected_pof **************

    def test_expected_pof_demo(self):
        fm = FailureMode.demo()
        fm.mc_timeline(200, n_iterations=1000)
        fm.expected_pof()

    def test_expected_pof(self):
        """ Check the Distribution returned by expected pof is within the tolerance expected"""
        param_untreated = [
            (100, 1, 10),
            (10, 1, 0),
            (10, 1, 10),
            (10, 3, 10),
            (50, 3, 10),
            (100, 3, 10),
        ]

        t_end = 100
        n_iterations = 1000

        for alpha, beta, gamma in param_untreated:
            # Arrange
            fm = FailureMode(untreated={"alpha": alpha, "beta": beta, "gamma": gamma})
            fm.mc_timeline(t_end=t_end, n_iterations=n_iterations)

            # Act
            treated = fm.expected_pof()

            # Assert
            for param in ["alpha", "beta", "gamma"]:
                actual = getattr(treated, param)
                expected = getattr(fm.dists["init"], param)
                delta = expected / 10
                self.assertAlmostEqual(actual, expected, delta=delta)

    # ------------ Integration Tests ---------------

    def test_init_dist_is_updated_on_creation(self):

        # Arrange / Act
        fm = FailureMode.from_dict(
            {"pf_interval": 10, "untreated": {"alpha": 100, "beta": 10, "gamma": 10}}
        )

        # Assert
        self.assertNotEqual(fm.untreated, fm.dists["init"])

    def test_init_dist_is_updated_with_untreated(self):

        # Arrange
        fm = FailureMode.from_dict(
            {"pf_interval": 10, "untreated": {"alpha": 100, "beta": 10, "gamma": 10}}
        )
        untreated = copy.copy(fm.dists.get("untreated", None))
        init = copy.copy(fm.dists.get("init", None))

        # Act
        fm.untreated = {"alpha": 50, "beta": 10, "gamma": 5}

        # Assert
        self.assertNotEqual(fm.dists["untreated"], untreated)
        self.assertNotEqual(fm.dists["init"], init)

    def test_init_dist_is_updated_with_pf_interval(self):

        # Arrange
        fm = FailureMode.from_dict(
            {"pf_interval": 10, "untreated": {"alpha": 100, "beta": 10, "gamma": 10}}
        )
        untreated = copy.copy(fm.dists.get("untreated", None))
        init = copy.copy(fm.dists.get("init", None))

        # Act
        fm.pf_interval = 5

        # Assert
        self.assertEqual(fm.dists["untreated"], untreated)
        self.assertNotEqual(fm.dists["init"], init)

    def test_init_dist_is_updated_with_update(self):
        """ Check that init dist updates when the update method is called on any of its inputs"""
        param_update = [
            {"pf_interval": 5},
            {"untreated": {"alpha": 80}},
        ]

        for update in param_update:

            # Arrange
            fm = FailureMode.from_dict(
                {
                    "pf_interval": 10,
                    "untreated": {"alpha": 100, "beta": 10, "gamma": 10},
                }
            )
            init = copy.copy(fm.dists.get("init", None))

            # Act
            fm.update(update)

            # Assert
            self.assertNotEqual(fm.dists["init"], init)


if __name__ == "__main__":
    unittest.main()
