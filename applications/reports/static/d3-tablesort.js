/*
 * d3 table sort
 * (c) Ilkka Huotari 2013, http : //ilkkah.com
 * Inspired by : http : //devforrest.com/examples/table/table.php
 * License : MIT
 */

(function (globals) {

    var sort_column = -1, // don't sort any column by default
        sort_order = 1, // desc
        min_cell_width = 5,
        max_cell_width = 30;

    globals.TableSort = function (table_title, table_id, columns, data, dimensions) {

        dimensions = dimensions || { width : '500px', height : '300px' };

        var dim = {
                w : dimensions.width,
                h : dimensions.height,
                tablew : dimensions.width,
                divh : (parseFloat(dimensions.height) - 100) + "px",
                divw : (parseFloat(dimensions.width) + 20) + "px",
                cell_widths : []
            },
            outerTable,
            innerTable,
            tbody,
            rows;

        for (var i=0, l=columns.length; i<l; i++) {
            var col_width = (columns[i].length+4 > min_cell_width) ? columns[i].length+4 : min_cell_width;
            col_width = col_width > max_cell_width ? max_cell_width : col_width;

            dim.cell_widths.push(col_width);
            for (var r=0, rl=data.length; r<rl; r++){
                build_column_length(i, data[r][i]);
            }
        }

        function build_column_length(index, text) {
            if (dim.cell_widths[index] < text.length) {
                dim.cell_widths[index] = (text.length < max_cell_width)? text.length : max_cell_width;
            }
        }

        function sort(d, tmp, i) {
            //var sort,
            var sort_btn = d3.select(d3.event.toElement || d3.event.target),
                is_desc = sort_btn.classed('sort_desc');

            sort_order = is_desc ? -1 : 1;
            sort_btn.classed('sort_desc', !is_desc).classed('sort_asc', is_desc);
            sort_column = i;
            tbody.selectAll("tr")
                .sort(function(a, b) {return TableSort.alphabetic(a[sort_column], b[sort_column], sort_order);});
        }

        outerTable = d3.select('#'+table_id).html(null)
            .append("table");
            //.attr("style", "width : " + dim.w);

        outerTable.append("tr")
            .append("td")
            .append("table").attr("class", "header-table")
            //.attr("style", "width : " + dim.tablew)
            .attr("margin-left", "10px")
            .append("tr").selectAll("th").data(columns).enter()
            .append("th")
            .text(function(d){return d;})
            .selectAll('span')
            .data(function (d, i) {return [d]; }).enter()
            .append('span')
            .classed('sort_indicator sort_desc', true)
            .on('click', sort);

        innerTable = outerTable
            .append("tr")
            .append("td")
            .append("div").attr("class", "scroll-table")
            //.attr("style", "width : " + dim.divw + ";")
            .append("table").attr("class", "body-table")
            .attr("style", "table-layout : fixed");
            //.attr("style", "width : " + dim.tablew + "; table-layout : fixed");

        tbody = innerTable.append("tbody");

        // Create a row for each object in the data and perform an intial sort.
        rows = tbody.selectAll("tr")
            .data(data)
            .enter()
            .append("tr");

        rows.datum(function (obj) {
            return obj;
        });

        rows.style('height', '30px');

        // initial sort
        if (sort_column >= 0) {
            tbody.selectAll('tr')
                .sort(function(a, b) {return TableSort.alphabetic(a[sort_column], b[sort_column], sort_order);})
        }

        // Create a cell in each row for each column
        rows.selectAll("td")
            .data(function (d) { return d; }).enter()
            .append("td")
            .style('width', function (d, i) { this.style.width = (dim.cell_widths[i]*9) + 'px'; return 1; })
            .text(function (d) { return d; });

        // set cell widths to the header-table
        outerTable.selectAll('.header-table tr th')
            .data(dim.cell_widths)
            .style('width', function (d) { this.style.width = (d*9+1) + 'px'; return 1; })

    };

    globals.TableSort.alphabetic = function (a, b, sort_order) { return sort_order * a.localeCompare(b); };
    globals.TableSort.numeric = function (a, b, sort_order) { return sort_order * (parseFloat(b) - parseFloat(a)); }

}(window));
