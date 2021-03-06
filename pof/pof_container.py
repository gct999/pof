""" A custom container for pof objects

The PofContainer behaves exactly like a dictionary with an additional update_from_dict method to ensure the key always matches the object name

"""

from collections import UserDict
import logging


class PofContainer(UserDict):
    """A dictionary that changes the key if the name of the pof object it is storing changes"""

    # def __init__(self, *args, **kwargs):
    #     self.data = dict()
    #     self.update(dict(*args, **kwargs))  # use the free update to set keys

    # def __getitem__(self, key):
    #     return self.data[key]

    # def __setitem__(self, key, value):
    #     self.data[key] = value

    # def __delitem__(self, key):
    #     del self.data[key]

    # def __iter__(self):
    #     return iter(self.data)

    # def __len__(self):
    #     return len(self.data)

    def __repr__(self):
        return f"{type(self).__name__}({self.data})"

    def update_from_dict(self, data):
        """Updates the pof objects in the container based on a dictionary input"""

        for key, details in data.items():

            # Update with the dictionary
            self.data[key].update_from_dict(details)

            # Check if the name has been updated
            new_key = self.data[key].name
            if key != new_key:

                logging.debug("Updating key to match name change")

                # Change the key if it is already in the dict
                new_key = rename_duplicate_key(
                    new_key=new_key, existing_keys=self.data.keys()
                )

                # Update the key
                self.data[key].name = new_key
                self.data[new_key] = self.data.pop(key)
                logging.debug("Key updated to %s", new_key)


def rename_duplicate_key(new_key, existing_keys):
    """ Renames a key if there is a duplicate in a list already"""
    i = 1
    base_key = new_key
    while new_key in existing_keys:
        logging.warning("Key %s is already in use", new_key)
        new_key = f"{base_key}|{i}"
        i = i + 1

    return new_key
