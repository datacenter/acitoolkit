################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""acitoolkitlib.py Test module
"""
from acitoolkit.aciTable import Table
import unittest


class TestTable(unittest.TestCase):
    """
    Test Table class from aciTable.py
    """
    def test_create_table(self):
        """
        Basic test
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+
|  header 1  |   header 2 |  header 3  |
+============+============+============+
|   cell11   |        1.2 |   cell13   |
+------------+------------+------------+
|   cell21   |       21   |   cell23   |
+------------+------------+------------+
|   cell31   |        3.2 |   cell33   |
+------------+------------+------------+
"""
        self.assertEqual(table_text, expected_table)

    def test_set_format(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title', tablefmt='simple')
        table_text = table.get_text()

        expected_table = """Test Title
 header 1     header 2   header 3
----------  ----------  ----------
  cell11           1.2    cell13
  cell21          21      cell23
  cell31           3.2    cell33
"""
        self.assertEqual(str(table_text), expected_table)

    def test_override_format(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text(tablefmt='simple')

        expected_table = """Test Title
 header 1     header 2   header 3
----------  ----------  ----------
  cell11           1.2    cell13
  cell21          21      cell23
  cell31           3.2    cell33
"""
        self.assertEqual(str(table_text), expected_table)

    def test_override_numalign(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text(numalign='right')

        expected_table = """Test Title
+------------+------------+------------+
|  header 1  |   header 2 |  header 3  |
+============+============+============+
|   cell11   |        1.2 |   cell13   |
+------------+------------+------------+
|   cell21   |         21 |   cell23   |
+------------+------------+------------+
|   cell31   |        3.2 |   cell33   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_set_numalign(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title', numalign='right')
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+
|  header 1  |   header 2 |  header 3  |
+============+============+============+
|   cell11   |        1.2 |   cell13   |
+------------+------------+------------+
|   cell21   |         21 |   cell23   |
+------------+------------+------------+
|   cell31   |        3.2 |   cell33   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_set_stralign(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title', stralign='right')
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+
|   header 1 |   header 2 |   header 3 |
+============+============+============+
|     cell11 |        1.2 |     cell13 |
+------------+------------+------------+
|     cell21 |       21   |     cell23 |
+------------+------------+------------+
|     cell31 |        3.2 |     cell33 |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_override_stralign(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text(stralign='right')

        expected_table = """Test Title
+------------+------------+------------+
|   header 1 |   header 2 |   header 3 |
+============+============+============+
|     cell11 |        1.2 |     cell13 |
+------------+------------+------------+
|     cell21 |       21   |     cell23 |
+------------+------------+------------+
|     cell31 |        3.2 |     cell33 |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_override_table_orientation(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text(table_orientation='vertical')

        expected_table = """Test Title
+----------+--------+--------+--------+
| header 1 | cell11 | cell21 | cell31 |
+----------+--------+--------+--------+
| header 2 |  1.2   |  21.0  |  3.20  |
+----------+--------+--------+--------+
| header 3 | cell13 | cell23 | cell33 |
+----------+--------+--------+--------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_set_table_orientation(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title', table_orientation='vertical')
        table_text = table.get_text()

        expected_table = """Test Title
+----------+--------+--------+--------+
| header 1 | cell11 | cell21 | cell31 |
+----------+--------+--------+--------+
| header 2 |  1.2   |  21.0  |  3.20  |
+----------+--------+--------+--------+
| header 3 | cell13 | cell23 | cell33 |
+----------+--------+--------+--------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_set_columns(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title', columns=2)
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+ +------------+------------+------------+
|  header 1  |   header 2 |  header 3  | |  header 1  |   header 2 |  header 3  |
+============+============+============+ +============+============+============+
|   cell11   |        1.2 |   cell13   | |   cell31   |        3.2 |   cell33   |
+------------+------------+------------+ +------------+------------+------------+
|   cell21   |       21   |   cell23   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_override_columns(self):
        """
        Checks that the format can be specified when the table is created

        :return:
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text(columns=2)

        expected_table = """Test Title
+------------+------------+------------+ +------------+------------+------------+
|  header 1  |   header 2 |  header 3  | |  header 1  |   header 2 |  header 3  |
+============+============+============+ +============+============+============+
|   cell11   |        1.2 |   cell13   | |   cell31   |        3.2 |   cell33   |
+------------+------------+------------+ +------------+------------+------------+
|   cell21   |       21   |   cell23   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_fix_none_in_data(self):
        """
        Checks that any cell with None as the data is converted to a space

        :return:
        """
        headers, data = self.get_data()
        data[1][1] = None
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+
|  header 1  |  header 2  |  header 3  |
+============+============+============+
|   cell11   |    1.2     |   cell13   |
+------------+------------+------------+
|   cell21   |            |   cell23   |
+------------+------------+------------+
|   cell31   |    3.20    |   cell33   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_fix_str_in_data(self):
        """
        Checks that any cell with None as the data is converted to a space

        :return:
        """
        headers, data = self.get_data()
        data[1][2] = 5
        table = Table(data, headers, title='Test Title')
        table_text = table.get_text()

        expected_table = """Test Title
+------------+------------+------------+
|  header 1  |   header 2 |  header 3  |
+============+============+============+
|   cell11   |        1.2 |   cell13   |
+------------+------------+------------+
|   cell21   |       21   |     5      |
+------------+------------+------------+
|   cell31   |        3.2 |   cell33   |
+------------+------------+------------+
"""
        self.assertEqual(str(table_text), expected_table)

    def test_flask_title(self):
        """
        Basic test
        """
        headers, data = self.get_data()
        table = Table(data, headers, title='Test Title')
        flask_title = table.title_flask

        self.assertEqual(flask_title, '"Test Title"')

    def get_data(self):
        """
        Will create table of switch context information
        :param title:
        :param contexts:
        """

        headers = ['header 1', 'header 2', 'header 3']
        data = [
            ['cell11', '1.2', 'cell13'],
            ['cell21', '21.0', 'cell23'],
            ['cell31', '3.20', 'cell33'],
        ]
        return headers, data

if __name__ == '__main__':

    offline = unittest.TestSuite()
    offline.addTest(unittest.makeSuite(TestTable))

    unittest.main()
