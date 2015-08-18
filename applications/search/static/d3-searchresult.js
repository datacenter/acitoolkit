/*

 <br>
 <hr>
 <h4>Name:{{ search_item['name']|safe }}</h4>
 <h4>Object:{{ search_item.object_type|safe }}</h4>
 <h4>Primary score:{{ search_item.pscore|safe }}</h4>
 <h4>Secondary score:{{ search_item.sscore|safe }}</h4>
 <h4>path{{ search_item.path|safe }}</h4>
 <h4>matching terms{{ search_item.terms|safe }}</h4>
 <br>
 <hr>
 {%  for table in search_item.report_table %}
 <script>
 </script>
 {%  endfor %}
 */

function searchResult(report) {

    function gen_summary(d) {
        var strng = "";
        strng += '<hr>';
        strng += "<h4>Name:"+d.name+ "</h4>";
        strng += "<p>Type:"+d.object_type+ "<br>";
        strng += 'Match score:' + d.pscore + '.' + d.sscore + '<br>';
        strng += 'Path:' + d.path + '<br>';
        strng += 'Matching terms:' + d.terms + '</p>';
        return strng;
    }
    // determine where to place it and create place holder
    d3.select(".span10").select("#content")
        .data(report)
        .append("div")
        //.attr("id", table_id)
        .attr("id", "records");

    d3.select(".span10").select("#content")
        .append("div")
        .attr("div", "report_table")
        //.attr("style", "width:600px;")
        .attr("margin-left", "90px")
        .select('#report_table').html(null);

    d3.select("#records")
        .selectAll("div")
        .data(report).enter().append("div")
        .attr("id",function(d, i) {return "record"+i;})
        .attr("class", "record")
        .append("div")
        .attr("class", "record_summary")
        .html(function (d) {return gen_summary(d);});

    d3.select("#records")
        .selectAll(".record")
        .append("div")
        .attr("class", "table_summary")

    for (var index in report) {
        var search_item = report[index];

        for (var table_index in search_item['report_table']) {
            var table = search_item['report_table'][table_index];
            var cleanKey = function (d) {
                return d.replace(/\//g, "_").replace(/\W/g, "_");
            };
            var table_data = table.data;
            var table_columns = table.headers;
            //
            var table_title = table.title_flask;

            var dimensions = {width: '600px', height: '400px'};
            var table_id = cleanKey('report_table' + table_title);


            if (table_data.length > 0) {
                TableSort(
                    table_title,
                    index,
                    table_columns,
                    table_data,
                    dimensions
                );
            }
        }
    }

}
