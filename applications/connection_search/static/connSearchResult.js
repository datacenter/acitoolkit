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
function showConnections(result) {
    var report = result['result'];

    // prep data
    var tempReport;
    var newReport = [];
    for (var i=0;i<report.length;i++){
        tempReport = [];
        tempReport.push(unwrap(report[i].sip));
        tempReport.push(unwrap(report[i].dip));
        tempReport.push(unwrap(report[i].filter));
        newReport.push(tempReport);

    }

    function unwrap(field){
        result = '';
        for (var j=0;j<field.length;j++){
            result += field[j] + '<br>'
        }
        return result
    }
    // determine where to place it and create place holder
    d3.select(".span10").select("#records")
        .remove();

    d3.select(".span10").select("#content")
        .data(report)
        .append("div")
        //.attr("id", table_id)
        .attr("id", "records");

    var outerTable = d3.select('#records')
        .append("table")
        .attr("border",1)
        //.attr("style","width:100%")
        .attr("class", "connectionTable");

    outerTable.selectAll("tr")
        .data(newReport).enter()
        .append("tr")
        .attr("id", function(d,i) {return "record"+i;})
        .selectAll("td")
        .data(function(d){return d;}).enter()
        .append("td")
        .html(function(d){return d;});

    spinner.stop();

    d3.select(".ac-searching").style("display", "none");
}
