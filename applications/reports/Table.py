#!/usr/bin/env python
# Copyright (c) 2015 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
class Table(object):
    
    @staticmethod
    def column(table_data, table_title):
        """
        Will build an N column table from table_data
        """
        # Determine number of columns
        num_columns = len(table_data)

        # Determine number of rows
        num_rows = 0
        for column in table_data:
            if num_rows < len(column):
                num_rows = len(column)
        
        # reformat into rows of columns
        data = []
        for row in range(num_rows):
            new_row = []
            
            for column in range(num_columns):
                if row < len(table_data[column]):
                    new_row.append(str(table_data[column][row][0]))
                    new_row.append(str(table_data[column][row][1]))
                else:
                    new_row.append('')
                    new_row.append('')
            data.append(new_row)

        # now build similar to other table
        num_columns = len(data[0])
        num_rows = len(data)
        
        #get column widths
        column_width = []
        for column in range(num_columns):
            if data[0][column]:
                column_width.append(len(data[0][column]))
            else:
                column_width.append(len('None'))
                                    
        for column in range(num_columns):
            for row in range(num_rows):
                if column_width[column] < len(data[row][column]):
                    column_width[column] = len(data[row][column])
                    
        # Get total width
        total_width = 0
        for column in range(num_columns):
            total_width += column_width[column]
        total_width += (num_columns-1)*3+2
            
        #build format strings
        format_title_line = '+{0:=^'+str(total_width)+'}+\n'
        format_title      = '{0:^'+str(total_width)+'}\n'
        format_line = '+'
        format_row = '|'
        for column in range(num_columns/2) :
            format_line += '{'+str(column*2)+':->'+str(column_width[column*2])+'}---'
            format_line += '{'+str(column*2+1)+':-<'+str(column_width[column*2+1])+'}'
            format_row += '{'+str(column*2)+':>'+str(column_width[column*2])+'} : '
            format_row += '{'+str(column*2+1)+':<'+str(column_width[column*2+1])+'}'
            if (column*2+1) < num_columns -1 :
                format_row += ' | '
                format_line+= '-+-'
                
        # build blank data for divider
        divider = []
        for column in range(num_columns):
            divider.append('')
            
        #build table
        text_string = ''
        if table_title :
            #text_string += format_title_line.format('')
            text_string += format_title.format(table_title)
            
        text_string += format_line.format(*divider)+'+\n'
        for row in range(0,num_rows):
            text_string += format_row.format(*data[row])+'|\n'
            
        text_string += format_line.format(*divider)+'+\n'
        return text_string

    @staticmethod
    def row_column(data, table_title = None):
        """
        Will build a table using the data.  Data is
        a list of table rows.
        """

        num_columns = len(data[0])
        num_rows = len(data)

        #fill out incomplete rows
        for row in range(num_rows):
            if len(data[row]) < num_columns:
                for column in range(len(data[row]),num_columns):
                    data[row].append('')
                    
        #get column widths
        column_width = []
        for column in range(num_columns):
            column_width.append(len(data[0][column]))
        for column in range(num_columns):
            for row in range(num_rows):
                if column_width[column] < len(data[row][column]):
                    column_width[column] = len(data[row][column])
        # Get total width
        total_width = 0
        for column in range(num_columns):
            total_width += column_width[column]
        total_width += (num_columns-1)*3+2
            
        #build format strings
        format_title_line = '+{0:=^'+str(total_width)+'}+\n'
        format_title      = '{0:^'+str(total_width)+'}\n'
        format_line = '+'
        format_div = '+'
        format_row = '|'
        for column in range(num_columns) :
            format_line += '{'+str(column)+':-^'+str(column_width[column])+'}'
            format_row += '{'+str(column)+':^'+str(column_width[column])+'}'
            format_div += '{'+str(column)+':=^'+str(column_width[column])+'}'
            if column < num_columns -1 :
                format_div += '=+='
                format_row += ' | '
                format_line+= '-+-'
                
        # build blank data for divider
        divider = []
        for column in range(num_columns):
            divider.append('')
            
        #build table
        text_string = ''
        if table_title :
            #text_string += format_title_line.format('')
            text_string += format_title.format(table_title)
            
        text_string += format_line.format(*divider)+'+\n'
        text_string += format_row.format(*data[0])+'|\n'
        text_string += format_div.format(*divider)+'+\n'
        for row in range(1,num_rows):
            text_string += format_row.format(*data[row])+'|\n'
            
        text_string += format_line.format(*divider)+'+\n'
        return text_string
    
