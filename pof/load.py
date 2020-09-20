from pof.config import Config as cf


"""
The load module is used to overload other pof classes so that they can use a common load methods
"""

# TODO add more robust error checking for types other than value error


class Load:
    """
    A class with methods for loading data that
    """

    @classmethod
    def load(cls, details=None):
        """
        Loads the data
        """
        try:
            instance = cls.from_dict(details)
        except ValueError as error:
            if cf.on_error_use_default:
                print("Error loading %s data - defaults used" % (cls.__name__))
                instance = cls()
            else:
                print("Error loading %s data" % (cls.__name__))
                raise error
        return instance

    @classmethod
    def from_dict(cls, details=None):
        """
        Unpacks the dictionary data and creates and object using the constructor
        """
        try:
            instance = cls(**details)
        except ValueError as error:
            if cf.on_error_use_default:
                print(
                    "Error loading %s data from dictionary - defaults used"
                    % (cls.__name__)
                )
                instance = cls()
            else:
                print("Error loading %s data from dictionary" % (cls.__name__))
                raise error

        return instance
