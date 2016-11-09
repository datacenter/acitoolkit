#!/usr/bin/env python
################################################################################
#               _    ____ ___   ____                       _                   #
#              / \  / ___|_ _| |  _ \ ___ _ __   ___  _ __| |_ ___             #
#             / _ \| |    | |  | |_) / _ \ '_ \ / _ \| '__| __/ __|            #
#            / ___ \ |___ | |  |  _ <  __/ |_) | (_) | |  | |_\__ \            #
#           /_/   \_\____|___| |_| \_\___| .__/ \___/|_|   \__|___/            #
#                                        |_|                                   #
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
"""
A table class that allows data and headers to be added to the class and then a nicely formatted table
retrieved from the class.

"""
from tabulate import tabulate


class Table(object):
    """
    Table object that holds the table data, headers, titles, and other control
    and then calls "tabulate" to format tables in various formats as needed and
    allows the data to be accessed in other formats.

    The headers are passed in as a list of strings.  One string for each column.
    The data is passed in as a list of rows where each rows is a list of values to
    be displayed in the same order as the headers.

    In some cases, a conventional table with a header row and data rows below it
    is not the ideal format.  Instead, it might be more desireable to have a list
    where the first column is the "header" or description, and the subsequent
    columns are the data.  To generate this kind of table, set the table_orientation
    attribute to "vertical".  The default is a traditional "horizontal" layout.

    The headers list is optional.

    Various plain-text table formats (`tablefmt`) are supported:
    'plain', 'simple', 'grid', 'pipe', 'orgtbl', 'rst', 'mediawiki',
    'latex', and 'latex_booktabs'.

    This class utilizes the `tabulate` python libarary to render the tables.  See
    the documenation at https://bitbucket.org/astanin/python-tabulate for details
    of the formatting options.
    """

    def __init__(self, data=(), headers=(), title=None, tablefmt='grid', floatfmt="g", numalign="decimal",
                 stralign="center",
                 missingval="", columns=1, table_orientation='horizontal'):
        """

        :param data: list of table data.  Each row is a list and each table is a list of rows
        :param headers: optional list of column headers
        :param title: optional title for the table
        :param tablefmt: table format - see above - default is 'grid'
        :param floatfmt: floating point number custom format string e.g. ".4f"
        :param numalign: number alignment - right, center, left, decimal - default is 'decimal'
        :param stralign: alignment for strings - right, center, left - default is 'center'
        :param missingval: alternate to use when a value is 'None' - default is ''
        :param columns: Number of columns to display table in.  Default is 1.  2 is implemented.
        :param table_orientation: Orientation - 'Horizontal' or 'Vertical'. Default is 'Horizontal'
        """
        # TODO: make table_orientation dynamic, i.e. determined based on the number of rows vs. number of columns.
        # TODO: make titles conform to tablefmt
        self.data = [
            [str(cell) if cell is not None else '' for cell in row]
            for row in data
        ]
        self.headers = headers
        self.tablefmt = tablefmt
        self.floatfmt = floatfmt
        self.numalign = numalign
        self.stralign = stralign
        self.missingval = missingval
        self.title = title
        self.columns = columns
        assert(table_orientation in ['horizontal', 'vertical'])
        self.table_orientation = table_orientation

    def get_text(self, title=None, tablefmt=None, floatfmt=None, numalign=None, stralign=None,
                 missingval=None, supresstitle=False, columns=None, table_orientation=None):
        """


        :param columns: Number of columns to target when table_orientation is "vertical"
        :param title: optional title string will over-ride configured title
        :param supresstitle: optional flag to supress title (default False)
        :param tablefmt: optional table format over-ride
        :param floatfmt: optional floating point format specifier over-ride
        :param numalign: optional number format specifier over-ride
        :param stralign: optional string alignment specifier over-ride
        :param missingval: optional missing value default specifier over-ride
        :param table_orientation: optional table orientation over-ride
        :return: str of the formatted table
        """
        if tablefmt is None:
            tablefmt = self.tablefmt
        if floatfmt is None:
            floatfmt = self.floatfmt
        if numalign is None:
            numalign = self.numalign
        if stralign is None:
            stralign = self.stralign
        if missingval is None:
            missingval = self.missingval
        if title is None:
            title = self.title
        if columns is None:
            columns = self.columns
        if table_orientation is None:
            table_orientation = self.table_orientation

        result = ''
        if table_orientation == 'vertical':

            if self.headers:
                assert len(self.data[0]) == len(self.headers),\
                    'Headers and Data have different lenghts - {0} and {1} respectively'\
                    .format(len(self.headers), len(self.data[0]))
                rows = [self.headers] + self.data
            else:
                rows = self.data
            table_data = list(zip(*rows))  # transpose table
            header_data = []
        else:
            table_data = self.data
            header_data = self.headers

        if columns == 1:
            result += tabulate(table_data, header_data, tablefmt=tablefmt, floatfmt=floatfmt,
                               numalign=numalign, stralign=stralign, missingval=missingval) + '\n'
        else:
            # Integer required for Python3
            table1_len = int((len(table_data) + 1) / 2)
            table2_len = len(table_data) - table1_len

            data1 = table_data[0:table1_len]
            data2 = table_data[table1_len:]
            result1 = tabulate(data1, header_data, tablefmt=tablefmt, floatfmt=floatfmt,
                               numalign=numalign, stralign=stralign, missingval=missingval)
            result2 = tabulate(data2, header_data, tablefmt=tablefmt, floatfmt=floatfmt,
                               numalign=numalign, stralign=stralign, missingval=missingval)
            t1 = result1.split('\n')
            t2 = result2.split('\n')
            result = ''
            for index in range(len(t2)):
                row = t1[index] + ' ' + t2[index] + '\n'
                result += row

            if table1_len > table2_len:
                result += t1[len(t1) - 2] + '\n'
                result += t1[len(t1) - 1] + '\n'

        if title and not supresstitle:
            result = title + '\n' + result
        return result

    @property
    def title_flask(self):
        """
        returns a flask friendly version of the title, i.e. enclosed in quotes.

        :return: "title"
        """
        return '\"' + self.title + '\"'

    # def multi_column(self, table_text):
    #     """
    #
    #     :return: new, multi-column table text
    #     """
    #     result = ''
    #     rows = table_text.split('\n')
    #     for index in range(len(rows)/2):
    #         result += rows[index]
    #         if (len(rows)/2 + index) < len(rows):
    #             result += rows[len(rows)/2 + index] + '\n'
    #         else:
    #             result += '\n'
    #
    #     return result
