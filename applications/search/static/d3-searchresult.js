/*
################################################################################
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
*/
function onClick_show_object(d) {
    // var uri = '/atk_object?dn='+d['path'];
    var uri = '/acitookkitselectsearchview?dn='+d['uid'];
    window.location.assign(encodeURI(uri))
}
function searchResult(result) {
    var report = result['result'];
    var total_hits = result['total_hits'];
    function gen_summary(d) {
        var strng = "";
        strng += '<hr>';
        strng += '<p class="record_title"><a href="/acitoolkitsearchview?dn='+ d.uid+'">'+d.class+': '+ d.name+'</a></p>';
        //strng += "<p>"+d.class+': '+d.name+ "</p>";
        strng += '<p style="color:green">' + d.uid + '</p>';
        strng += "<p>";
        strng += 'Match score:' + d.pscore + '.' + d.sscore + ', ';
        strng += 'Matching terms:[' + d.terms + ']</p>';
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
        .on("click", function (d) { onClick_show_object(d); });

    spinner.stop();

    if (report.length==0) {
        d3.select('.ac-searching').text('No results').style("display", "block");
    } else {
        var index = report.length;
        d3.select('.ac-searching').text('Showing '+index+' of ' + total_hits+' results').style("display", "block");

    }

}
