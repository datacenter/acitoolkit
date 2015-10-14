/**
 Copyright (c) 2014 BrightPoint Consulting, Inc.

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use, 
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
 */
function autoComplete(keywords, values, callBack) {
    var margin = {top: 20, right: 10, bottom: 10, left: 10},
        width = 100 - margin.left - margin.right,
        height = 100 - margin.top - margin.bottom;
    var currentSearchString = '',
        lastSearchString,
        selectedCallBack = callBack;
    var searchTerms = [];
    var onSpaceDone = false;

    var container = d3.select("body").select("#autoComplete");
    var enter = container.append("div")
        .attr("id", "ac")
        .attr("class", "ac")
        .append("div")
        .attr("class", "blank-row")
        .append("div")
        .attr("style", "ac-holder");

    container.attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom);

    var input = enter.append("input")
        .attr("class", "ac-form-control")
        .attr("placeholder", "Search: enter object, attribute, or value")
        .attr("type", "text")
        .on("keyup", onKeyUp);

    var sButton = enter.append("input")
        .attr("type", "button")
        .attr("class", "ac-submit-control")
        .attr("value", "search")
        .on("click", sButtonSelect);

    var reloadCheck = enter.append("input")
        .attr("type", "checkbox")
        .attr("class", "ac-submit-control")
        .attr("value", "reload");

    var searching = enter.append("div").attr("class", "ac-searching")
        .text("Enter one or more objects, attributes or values");

    var dropDown = enter.append("div").attr("class", "ac-dropdown")
                        .style("display", "none");


    function showSearching(value) {
        searching.style("display", "block");
        searching.text(value);
    }

    // checks to see if the newTerm has some characters
    // and it is different from the oldTerm
    function isNewSearchNeeded(newTerm, oldTerm) {
        return newTerm.length >= 1 && newTerm != oldTerm;
    }

    function onKeyUp() {
        var searchString = input.node().value.trim().replace(/\s\s+/g, ' ');
        var subSearchString = searchString.split(' ').pop();
        var e = d3.event;
        console.log('key is '+e.which);
        if (!(e.which === 38 || e.which === 40 || e.which === 13 || e.which===32)) {
            // is up/down arrow or enter
            if (!subSearchString || subSearchString === "") {
                showSearching("No results");
                hideDropDown();
                lastSearchString = "";
            } else if (isNewSearchNeeded(subSearchString, lastSearchString)) {
                lastSearchString = subSearchString;
                showSearching();
                search(subSearchString);
                processResults(subSearchString);
                if (matches.length === 0) {
                    showSearching("No results");
                }
                else {
                    hideSearching();
                    showDropDown();
                }
            }

        } else {
            if (e.which===32) {
                console.log('Space');
                onSpace();
            }
            if (e.which===13) {
                console.log('Done');
                hideDropDown();
                showSearching("Searching...");
                selectedCallBack(input.node().value);
                searchTerms = [];
            }

        }

    }

    // this will search for the searchString in the portData
    // array and update the matches array with all the ones
    // that match.
    // It will anchor the search at the beginning of the string
    // Changing the comparison to 'indexOf' from == 0 to >= 0 will
    // allow the search to match anywhere.
    function search(searchString) {

        var str = searchString;
        console.log("searching on " + searchString.split(' '));

        var matches = [];
        var match=false;
        onSpaceDone = false;  // allow the matched item to be added with a <sp>
        for (var i = 0; i < keywords.length; i++) {
            match = (keywords[i].toLowerCase().indexOf(str.toLowerCase()) == 0);
            if (match) {
                matches.push(keywords[i]);
                // console.log("matches " + keywords[i]);
            }
        }
        for (var j = 0; j < values.length; j++) {
            match = (values[j].toLowerCase().indexOf(str.toLowerCase()) == 0);
            if (match) {
                matches.push(values[j]);
                // console.log("matches " + values[i]);
            }
        }
    }

    function processResults(searchString) {

        var results = dropDown.selectAll(".ac-row").data(matches, function (d) {return d;});
        results.enter()
            .append("div").attr("class", "ac-row")
            .on("click", function (d) { row_onClick(d); })
            .append("div").attr("class", "ac-title")
            .html(function (d) {
                var re = new RegExp(searchString, 'i');
                var strPart = d.match(re)[0];
                return d.replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>");
            });

        results.exit().remove();

        //Update results

        results.select(".ac-title")
            .html(function (d, i) {
                var re = new RegExp(searchString, 'i');
                var strPart = matches[i].match(re);
                if (strPart) {
                    strPart = strPart[0];
                    return matches[i].replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>");
                }

            });
    }
    function showDropDown() {
        dropDown.style("display", "block");
    }
    function hideSearching() {
        searching.style("display", "none");
    }

    function hideDropDown() {
        dropDown.style("display", "none");
    }

    function row_onClick(d) {
        hideDropDown();
        searchTerms = input.node().value.replace(/\s\s+/g, ' ').trim().split(' ');
        searchTerms.pop();
        searchTerms.push(d);
        input.node().value = searchTerms.join(' ');
    }

    function onSpace() {
        hideDropDown();
        searchTerms = input.node().value.replace(/\s\s+/g, ' ').trim().split(' ');
        if (onSpaceDone===false) {
            searchTerms.pop();
            lastSearchString = '';
            searchTerms.push(matches[0]);
        }
        onSpaceDone = true;
        input.node().value = searchTerms.join(' ') + ' ';
    }

    function defaultSelectedCallBack(d) {
        console.log(d + " selected");
    }
    function sButtonSelect() {
        console.log("sButton selected");
        hideDropDown();
        showSearching("Searching...");
        selectedCallBack(input.node().value);
        searchTerms = [];
    }
}

