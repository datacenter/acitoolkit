function onClick_show_object(d) {
    var uri = '/atk_object?dn='+d['path']
    window.location.assign(encodeURI(uri))
}
function searchResult(result) {
    var report = result['result'];
    var total_hits = result['total_hits'];
    function gen_summary(d) {
        var strng = "";
        strng += '<hr>';
        strng += "<h4>"+d.name+ "</h4>";
        strng += 'Path:' + d.path + '<br>';
        strng += "<p>Class:"+d.object_type+ ", ";
        strng += 'Match score:' + d.pscore + '.' + d.sscore + ', ';
        strng += 'Matching terms:' + d.terms + '</p>';
        return strng;
    }
    // determine where to place it and create place holder
    d3.select(".span10").select("#records")
        .remove();

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
        .html(function (d) {return gen_summary(d);})
        .on("click", function (d, i) { onClick_show_object(d); });


    if (report.length==0) {
        d3.select('.ac-searching').text('No results').style("display", "block");
    } else {
        index = report.length;
        d3.select('.ac-searching').text('Showing '+index+' of ' + total_hits+' results').style("display", "block");

    }

}
