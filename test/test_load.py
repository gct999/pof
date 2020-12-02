"""
    Filename: test_load.py
    Description: Contains the code for testing the Constructor class
    Author:
        Gavin Treseder | gct999@gmail.com | gtreseder@kpmg.com.au | gavin.treseder@essentialenergy.com.au
        Illyse Schram  | ischram@kpmg.com.au | illyse.schram@essentialenergy.com.au
"""

import unittest
from unittest.mock import Mock, patch

import fixtures
import testconfig  # pylint: disable=unused-import
from pof.load import Load
from pof.units import valid_units


class TestPofBase(object):
    """
    An abstract test class that contains a collection of tests to test a from_dict method for a pof object

    Needs to include a setUp() method that includes:
        self._class
                        Used for calling class methods

        self._data_valid
        self._data_invalid_values
        self._data_invalid_types

    """

    tc = unittest.TestCase()

    def setUp(self):
        """
        Set up the test so errors are returned if test data is not overloaded
        """

        # Config for checking default behaviour
        self.blank_config = Mock()
        self.blank_config.get.return_value = None

        # Class data
        self._class = Mock(spec=object, return_value=None)
        self._class.from_dict = Mock(return_value=None)
        self._class._scale_units = Mock(return_value=None)  # TODO

        # Valid and invalid Data that will cause errors if not overloaded
        self._data_valid = [Mock(return_value=None)]
        self._data_invalid_values = [{"name": "name"}]
        self._data_invalid_types = [{"name": "name"}]
        self._data_complete = [Mock(return_value=None)]

    # ---------------- Class Instantiate ------------------------

    def test_class_instantiate_with_no_data(self):
        """ Check class instantiate works with all no data"""
        # Arrange
        class_config = "pof.load.cf"
        for param in [True, False, None]:
            with patch.dict(class_config, {"handle_invalid_data": param}):

                # Act
                instance = self._class()

                # Assert
                self.tc.assertIsNotNone(instance)

    def test_class_instantiate_with_valid_data(self):
        """ Check class instantiate works with valid data"""

        # Arrange
        class_config = "pof.load.cf"
        for param in [True, False, None]:
            with patch.dict(class_config, {"handle_invalid_data": param}):

                for data in self._data_valid:
                    # Act
                    instance = self._class(**data)

                    # Assert
                    self.tc.assertIsNotNone(instance)

    def test_class_instantiate_with_invalid_data(self):

        # Arrange
        class_config = "pof.load.cf"
        with patch.dict(class_config, {"handle_invalid_data": True}):
            invalid_data = self._data_invalid_types
            for data in invalid_data:

                # Act
                instance = self._class(**data)

                # Assert
                self.tc.assertIsNotNone(instance)
                self.tc.assertTrue(isinstance(instance, self._class))

        with patch.dict(class_config, {"handle_invalid_data": False}):
            invalid_data = self._data_invalid_types
            for data in invalid_data:

                # Act / Assert
                with self.tc.assertRaises(TypeError):
                    instance = self._class(**data)

    # ---------------- Test from_dict ----------------

    def test_from_dict_no_data(self):
        with self.tc.assertRaises(TypeError):
            self._class.from_dict()

    def test_from_dict_with_valid_data(self):
        for data in self._data_valid:
            instance = self._class.from_dict(data)
            self.tc.assertIsNotNone(instance)

    def test_from_dict_with_invalid_data(self):
        """ Check invalid data is handled correctly"""

        # Arrange
        class_config = "pof.load.cf"
        with patch.dict(class_config, {"handle_invalid_data": False}):

            # Act / Assert
            # for invalid_type in self._data_invalid_types:
            #     with self.tc.assertRaises(TypeError):
            #         self._class.from_dict(invalid_type)

            for invalid_value in self._data_invalid_values:
                with self.tc.assertRaises(ValueError):
                    self._class.from_dict(invalid_value)

    def test_from_dict_with_complete_data(self):
        # Arrange
        class_config = "pof.load.cf"

        with patch.dict(class_config, {"handle_invalid_data": False}):
            with patch.dict(class_config, {"on_error_use_default": False}):
                for data in self._data_complete:
                    # Act
                    instance = self._class.from_dict(data)

                    # Assert
                    self.tc.assertIsNotNone(instance)
                    self.tc.assertTrue(isinstance(instance, self._class))

    # ************ Test load ***********************

    def test_load_with_empty(self):
        instance = self._class.load()
        self.tc.assertIsNotNone(instance)
        self.tc.assertTrue(isinstance(instance, self._class))

    def test_load_valid_dict(self):
        for data in self._data_valid:
            # Arrange
            instance_from_dict = self._class.from_dict(data)

            # Act
            instance = self._class.load(data)

            # Assert
            self.tc.assertTrue(isinstance(instance, self._class))
            self.tc.assertEqual(instance, instance_from_dict)

    def test_load_with_invalid_data_errors_managed(self):

        # Arrange
        # class_config = self._class.__module__ + ".cf"
        class_config = "pof.load.cf"

        with patch.dict(class_config, {"handle_invalid_data": False}):
            with patch.dict(class_config, {"on_error_use_default": False}):

                # Act / Assert
                for data in self._data_invalid_types:
                    with self.tc.assertRaises(TypeError):
                        self._class.from_dict(data)

                for data in self._data_invalid_values:
                    with self.tc.assertRaises(ValueError):
                        self._class.from_dict(data)

            with patch.dict(class_config, {"on_error_use_default": True}):
                invalid_data = self._data_invalid_types + self._data_invalid_values
                for data in invalid_data:

                    # Act  / Assert
                    instance = self._class.load(data)

                    # Assert
                    self.tc.assertIsNotNone(instance)
                    self.tc.assertTrue(isinstance(instance, self._class))

    # ************ Test load ***********************

    def test_demo(self):

        # Arrange / Act / Assert
        self.tc.assertIsNotNone(self._class.demo())

    # ************ Test __ methods __

    def test_equivalence(self):

        # Arrange / Act
        inst_1 = self._class.demo()
        inst_2 = self._class.demo()
        inst_3 = self._class(name="a different name")

        # Assert
        self.tc.assertTrue(inst_1 == inst_2)
        self.tc.assertTrue(inst_2 == inst_1)
        self.tc.assertTrue(inst_1 != inst_3)
        self.tc.assertTrue(inst_3 != inst_1)
        self.tc.assertTrue(not (inst_1 is inst_2))
        self.tc.assertTrue(not (inst_2 is inst_3))

    # *************** Test Update *************

    def test_update(self):

        # Arrange
        data = self._data_complete[0]
        instance_0 = self._class.from_dict(data)
        instance_1 = self._class.from_dict(self._data_complete[1])

        with patch.dict("pof.load.cf", {"handle_update_error": False}):

            # Act
            instance_1.update(data)

        msg = []
        for key, val in instance_0.__dict__.items():
            if instance_1.__dict__[key] != val:
                msg.append((key, val))

        # Assert
        self.tc.assertEqual(instance_0, instance_1, msg=msg)

    def test_update_errors_logged(self):
        """ Checks that an error is raised when invalid input data is provided"""
        # Arrange
        class_config = "pof.load.cf"
        instance = self._class.demo()

        invalid_data = self._data_invalid_types + self._data_invalid_values

        for data in invalid_data:
            with patch.dict(class_config, {"handle_update_error": True}):
                with self.tc.assertLogs(level="DEBUG") as log:
                    # Act
                    instance.update(data)

                    # Assert
                    self.tc.assertTrue("Update Failed" in log.output[-1])

    def test_update_errors_raised(self):
        """ Checks that an error is raised when invalid input data is provided"""
        # Arrange
        class_config = "pof.load.cf"
        instance = self._class.demo()

        invalid_data = self._data_invalid_types + self._data_invalid_values

        for data in invalid_data:
            with patch.dict(class_config, {"handle_update_error": False}):
                with self.tc.assertRaises((ValueError, AttributeError, KeyError)):
                    # Act
                    instance.update(data)

    # ************* Test units ******************

    def test_units_undefined(self):
        """ Case when current_units is not defined, sets to None & self._units = value """

        # Arrange
        input_data = ["seconds", "minutes", "hours", "days", "weeks", "months", "years"]

        for val in input_data:
            # Act
            instance = self._class.from_dict(self._data_complete[0])
            instance.units = val

            # Assert
            self.tc.assertEqual(instance.units, val)

    def test_units_invalid(self):
        """ Case when value not in valid units raises error """

        # Arrange
        input_data = ["test"]

        for val in input_data:
            # Act
            instance = self._class.from_dict(self._data_complete[0])

            # Assert
            with self.tc.assertRaises(ValueError):
                instance.units = val

    def test_units_defined(self):
        """Case when current_units is defined, but equal to value, set self._units = value
        && Case when current_units is not None & not equal to value, calls self._scale_units then sets self._units = value"""

        # Arrange
        input_data = ["months", "years"]

        # Act
        instance = self._class.from_dict(self._data_complete[0])
        mock = Mock()

        for val in input_data:
            instance.units = val

            mock._scale_units(val, "years")

            # if getattr(self.tc, instance.units) == val:
            # mock that the scale units call was triggered
            # mock._scale_units.assert_called_with(val, getattr(self.tc, instance.units))

            # Assert
            self.tc.assertEqual(instance.units, val)


class TestLoad(TestPofBase, unittest.TestCase):
    def setUp(self):

        # PofBase
        self._class = Load
        self._data_valid = [{"name": "name"}]
        self._data_invalid_values = [{"name": 1234}]
        self._data_invalid_types = [{"invalid_type": "invalid_type"}]
        self._data_complete = [{"name": "name_0"}, {"name": "name_1"}]

        # Mock the pof object
        self.pof_obj = Mock()
        self.pof_obj.name = "mock_name"
        self.pof_obj.load.return_value = Mock()

        # Create a load object with every type of data store
        self.load = Load(name="before_update")
        self.load.obj = Load(name="before_update")
        self.load.dict_obj = dict(test_key=Load(name="before_update"))

    def test_scale_units(self):
        """Case when Time_variables has length > 1, updates all variables
        && when Pof_variables has a dict and a string, updates all correctly"""

        for key in valid_units:
            # Arrange
            load = Load()
            current_unit = "hours"

            load.TIME_VARIABLES = ["test_time_1", "test_time_2"]
            load.test_time_1 = 1
            load.test_time_2 = 1

            load.POF_VARIABLES = ["obj", "dict_obj"]
            load.obj = Load(units=current_unit)
            load.dict_obj = dict(obj_key=Load(units=current_unit))
            
            # Act
            load._scale_units(key, current_unit)

            # Assert - Time_variables
            for var in load.TIME_VARIABLES:
                self.assertAlmostEquals(getattr(load, var), 1 / valid_units[key])

            # Assert - Pof_variables
            self.assertEqual(load.obj.units, key)
            self.assertEqual(load.dict_obj["obj_key"].units, key)

    def test_scale_units_zero(self):
        """ Case when getattr of a time_variable is 0, should return 0"""

        # Arrange
        load = Load()
        current_unit = "hours"

        load.TIME_VARIABLES = ["test_time_3"]
        load.test_time_3 = 0
        load.POF_VARIABLES = []

        for key in valid_units:
            # Act
            load._scale_units(key, current_unit)

            # Assert
            for var in load.TIME_VARIABLES:
                self.assertAlmostEquals(getattr(load, var), 0)

    def test_scale_units_error(self):
        """ Case when var is None raise value error """
        # Arrange
        load = Load()
        current_unit = "hours"

        load.POF_VARIABLES = ["test_pof_3"]
        load.test_pof_3 = None

        for key in valid_units:
            # Assert && Act
            with self.assertRaises(ValueError):
                load._scale_units(key, current_unit)

    # ------------ set_containter_attr with empty container -----------

    def test_set_obj_from_dict(self):

        # Arrange
        load = Load()
        load.dict_obj = None
        test_data = dict(name="test")
        expected = Load(name="test")

        # Act
        load.set_obj("dict_obj", Load, test_data)

        # Assert
        self.assertEqual(load.dict_obj[expected.name], expected)

    def test_set_obj_from_dict_of_dicts(self):

        load = Load()
        test_data = dict(pof_object=dict(name="test"))
        expected = Load(name="test")

        load.set_obj("obj", Load, test_data)

        self.assertEqual(load.obj[expected.name], expected)

    def test_set_obj_from_dict_of_objects(self):

        # Arrange
        load = Load()
        load.dict_obj = None
        test_data = {"test_key": Load(name="test")}
        expected = Load(name="test")

        # Act
        load.set_obj("dict_obj", Load, test_data)

        # Assert
        self.assertEqual(load.dict_obj[expected.name], expected)

    def test_set_obj_from_object(self):

        load = Load()
        test_data = Load(name="test")
        expected = Load(name="test")

        load.set_obj("obj", Load, test_data)

        self.assertEqual(load.obj[expected.name], expected)

    # ------------ set_containter_attr with existing data -----------

    def test_set_obj_existing_data_from_dict(self):

        load = Load()
        load.obj = dict(test=Load(name="this_should_change"))
        test_data = dict(name="test")
        expected = Load(name="test")

        load.set_obj("obj", Load, test_data)

        self.assertEqual(load.obj[expected.name], expected)

    def test_set_obj_existing_data_from_dict_of_dicts(self):

        load = Load()
        load.obj = dict(test=Load(name="this_should_change"))
        test_data = dict(pof_object=Load(name="test"))
        expected = Load(name="test")

        load.set_obj("obj", Load, test_data)

        self.assertEqual(load.obj[expected.name], expected)

    def test_set_obj_existing_data_from_dict_of_objects(self):

        load = Load()
        load.obj = dict(test=Load(name="this_should_change"))
        test_data = dict(pof_object=Load(name="test"))
        expected = Load(name="after_update")
        key_before_update = "test"

        load.set_obj("obj", Load, test_data)
        test_data["pof_object"].name = "after_update"

        self.assertEqual(load.obj[key_before_update], expected)

    def test_set_obj_existing_data_from_object(self):

        load = Load()
        load.obj = dict(test=Load(name="this_should_change"))
        test_data = Load(name="test")
        expected = Load(name="after_update")
        key_before_update = "test"

        load.set_obj("obj", Load, test_data)
        test_data.name = "after_update"

        self.assertEqual(load.obj[key_before_update], expected)

    # -------------------- Test update -----------------------------

    def test_update_errors_caught_and_logged(self):
        """ check that an attriubte that doens't exist returns a Key Error"""
        # Arrange
        load = Load(name="before_update")
        load.data = "before_update"
        load.obj = Load(name="before_update")
        load.dict_data = {"test_key": "before_update"}
        load.dict_obj = {"test_key": Load(name="before_update")}

        param_tests = [
            ({"invalid_attribute": "after_update"}),
            ({"obj": {"invalid_attribute": "after_update"}},),
            ({"dict_data": {"invalid_key": "after_update"}}),
            ({"dict_obj": {"invalid_key": {"name": "after_update"}}},),
        ]

        for test_data in param_tests:
            with self.tc.assertLogs(level="DEBUG") as log:
                # Act
                load.update(test_data)

                # Assert
                # TODO check errorhas been looged
                # self.tc.assertTrue("Update Failed" in log.output[-1])

    # -------------------- Test update_from_str -----------------------------

    def test_update_from_str(self):
        """ Check a string is converted to a dict for subsequent updates"""
        # Arrange
        load = Load(name="test_load")
        load.data = "before_update"

        id_str = "Load-test_load-data"
        value = "after_update"
        sep = "-"

        # Act
        load.update_from_str(id_str=id_str, value=value, sep=sep)

        # Assert
        self.assertEqual(load.data, "after_update")

    # -------------------- Test update_from_dict --------------------

    def test_update_from_dict_to_update_data(self):
        """ Check an attribute can be updated"""
        # Arrange
        load = Load(name="no_update")
        load.obj = Load(name="no_update")
        load.dict_obj = {"test_key": Load(name="no_update")}
        test_data = {"name": "after_update"}

        # Act
        load.update_from_dict(test_data)

        # Assert
        self.assertEqual(load.name, "after_update")

    def test_update_from_dict_to_update_object(self):
        """ Check an attribute that is another pof object can be updated"""
        # Arrange
        load = Load(name="no_update")
        load.obj = Load(name="no_update")
        test_data = {"obj": {"name": "after_update"}}

        # Act
        load.update_from_dict(test_data)

        # Assert
        self.assertEqual(load.obj.name, "after_update")

    def test_update_from_dict_to_update_dict_of_data(self):
        """ Check a dictionary of data can be updated"""

        # Arrange
        load = Load(name="no_update")
        load.dict_data = {"test_key": "no_update"}
        test_data = {"dict_data": {"test_key": "after_update"}}

        # Act
        load.update_from_dict(test_data)

        # Assert
        self.assertEqual(load.dict_data["test_key"], "after_update")

    def test_update_from_dict_to_update_dict_of_objects(self):
        """ Check a dictionary of pof objects can be updated"""

        # Arrange
        load = Load(name="no_update")
        load.dict_obj = {"test_key": Load(name="no_update")}
        test_data = {"dict_obj": {"test_key": {"name": "after_update"}}}

        # Act
        load.update_from_dict(test_data)

        # Assert
        self.assertEqual(load.dict_obj["test_key"].name, "after_update")

    def test_update_from_dict_with_multiple_values_at_once(self):
        """ Check multiple attributes that exist can be updated at once"""

        # Arrange
        load = Load(name="before_update")
        load.obj = Load(name="before_update")
        load.dict_data = {"test_key": "before_update"}
        load.dict_obj = {"test_key": Load(name="before_update")}
        test_data = dict(
            name="after_update",
            obj={"name": "after_update"},
            dict_data={"test_key": "after_update"},
            dict_obj={"test_key": {"name": "after_update"}},
        )

        # Act
        load.update_from_dict(test_data)

        # Assert
        self.assertEqual(load.name, "after_update")
        self.assertEqual(load.obj.name, "after_update")
        self.assertEqual(load.dict_data["test_key"], "after_update")
        self.assertEqual(load.dict_obj["test_key"].name, "after_update")

    def test_update_from_dict_with_errors_expected(self):
        """ check that an attriubte that doens't exist returns a Key Error"""
        # Arrange
        load = Load(name="before_update")
        load.data = "before_update"
        load.obj = Load(name="before_update")
        load.dict_data = {"test_key": "before_update"}
        load.dict_obj = {"test_key": Load(name="before_update")}

        param_tests = [
            (
                AttributeError,
                {"invalid_attribute": "after_update"},
            ),
            (
                AttributeError,
                {"obj": {"invalid_attribute": "after_update"}},
            ),
            (
                KeyError,
                {"dict_data": {"invalid_key": "after_update"}},
            ),
            (
                KeyError,
                {"dict_obj": {"invalid_key": {"name": "after_update"}}},
            ),
        ]

        for error, test_data in param_tests:
            # Act / Assert
            with self.assertRaises(error):
                load.update_from_dict(test_data)


if __name__ == "__main__":
    unittest.main()
