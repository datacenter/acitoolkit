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

    var showTip = function(d, i) {
        var row = d3.event.target.parentNode.id;
        var patt1 = /[0-9]+/g;
        var result = row.match(patt1);
        var tip="";
        if (i==0) {
            tip += report[parseInt(result)].sourceEpg;
        } else if (i==1) {
             tip += report[parseInt(result)].destEpg;
        } else {
            tip = report[parseInt(result)].tenant + "::" + report[parseInt(result)].contract;
        }
        buildSideBar(parseInt(result));
    };

    var hideTip = function(d) {
        //d3.selectAll("#legend").remove();
    };

    var buildSideBar = function(row) {
        // will build a form that shows source epg, dest epg, and contract

        offset1 = 20;
        offset2 = 23;
        offset3 = 33;
        var data = {"text":["Tenant: "+report[row].src_tenant,
            report[row].src_app_profile_type+ ": " + report[row].src_app_profile,
            report[row].src_epg_type+ ": " +report[row].sourceEpg,
            "Tenant: "+report[row].dst_tenant,
            report[row].dst_app_profile_type+ ": " + report[row].dst_app_profile,
            report[row].dst_epg_type+ ":" +report[row].destEpg,
            "Tenant: " + report[row].contract_tenant,
            "Contract: " + report[row].contract],
            "offset":[offset1, offset1, offset1, offset2, offset2, offset2, offset3, offset3]
            }

        var height = 400;
            // .attr("style", "position:absolute; top:0px; left:0px");
        svgContainer.transition()
            .duration(200)
            .style("opacity", 1);

        //Draw the Rectangle
        d3.selectAll("#legend").remove();
        var sourceText = svgContainer.selectAll("#legend")
            .data(data["text"])
            .enter()
            .append("text")
            .attr("id", "legend");

        var textLabels = sourceText
               .attr("x", function(d) { return 35; })
               .attr("y", function(d, i) { return data["offset"][i]+(i * 20); })
               .text( function (d) {return d;})
               .attr("font-family", "Helvetica Neue, Helvetica, Arial, sans-serif")
               .attr("font-size", "12px")
               .attr("fill", "white");
    };

    var hideSideBar = function(d) {
        svgContainer.transition()
            .duration(200)
            .style("opacity", 0);

    }

    // determine where to place it and create place holder
    d3.select(".span10").select("#records")
        .remove();

    d3.select(".span10").select("#content")
        .data(report)
        .append("div")
        //.attr("id", table_id)
        .attr("id", "records");

    var tableHeader = d3.select('#records')
        .append('table')
        .attr("style", "width: 600px;")
        .attr("cellpadding", "0")
        .attr("cellspacing", "0")
        .append("tr")
        .attr("class", "border_bottom");

    tableHeader.append("th")
        .attr("style", "width:175px")
        .attr("align", "center")
        .text("Source IP");
    tableHeader.append("th")
        .attr("style", "width:175px")
        .attr("align", "center")
        .text("Destination IP");
    tableHeader.append("th")
        .attr("style", "width:200px")
        .attr("align", "center")
        .text("Filter");

    var outerTable = d3.select('#records')
        .append('div')
        .attr("style","overflow: auto;height: 500px; width: 620px; float:left")
        .append("table")
        .attr("style", "width: 600px;")
        .attr("cellpadding", "0")
        .attr("cellspacing", "0")
        .attr("border",1)
        //.attr("style","width:100%")
        .attr("class", "connectionTable")
        .on("mouseout", function(d) {hideSideBar(d);});


    tableRow = outerTable.selectAll("tr")
        .data(newReport).enter()
        .append("tr")
        .attr("id", function(d,i) {return "record"+i;});

    tableRow.append('td')
        .attr("style", "width:175px")
        .html(function (d) { return d[0];})
        .on("mouseover", function(d, i) {showTip(d[0], 0);})
        .on("mouseout", function(d) {hideTip(d[0]);});

    tableRow.append('td')
        .attr("style", "width:175px")
        .html(function (d) { return d[1];})
        .on("mouseover", function(d, i) {showTip(d[1], 1);})
        .on("mouseout", function(d) {hideTip(d[1]);});

    tableRow.append('td')
        .attr("style", "width:300px")
        .html(function (d) { return d[2];})
        .on("mouseover", function(d, i) {showTip(d[2], 2);})
        .on("mouseout", function(d) {hideTip(d[2]);});


    spinner.stop();

    d3.select(".ac-searching").style("display", "none");

    var svgContainer = d3.select('#records')
        .append("svg")
        .attr("width", 250)
        .attr("height", 400)
        .style("opacity", 0);

    var rectangle = svgContainer.append("rect")
        .attr("x", 10)
        .attr("y", 0)
        .attr("width", 225)
        .attr("height", 200)
        .style("opacity",0.5)
        .attr("fill", "#0088cc");
    var boxHeight = 60;
    var srcRect = svgContainer.append("rect")
        .attr("x", 30)
        .attr("y", 5)
        .attr("width", 200)
        .attr("height", boxHeight)
        .style("opacity",1)
        .attr("fill", "#0088cc");

    var dstRect = svgContainer.append("rect")
        .attr("x", 30)
        .attr("y", 5 + boxHeight+5)
        .attr("width", 200)
        .attr("height", boxHeight)
        .style("opacity",1)
        .attr("fill", "#0088cc");

    var fltRect = svgContainer.append("rect")
        .attr("x", 30)
        .attr("y", 5+boxHeight+5+boxHeight+5)
        .attr("width", 200)
        .attr("height", boxHeight)
        .style("opacity",1)
        .attr("fill", "#0088cc");

    svgContainer.append("text")
        .text("Source")
        .attr("x", -56)
        .attr("y", 25)
        .attr("transform", "rotate(-90)")

    svgContainer.append("text")
        .text("Dest")
        .attr("x", -116)
        .attr("y", 25)
        .attr("transform", "rotate(-90)")

    svgContainer.append("text")
        .text("Contract")
        .attr("x", -193)
        .attr("y", 25)
        .attr("transform", "rotate(-90)")
}
