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
Array.prototype.extend = function (other_array) {
    /* you should include a test to check whether other_array really is an array */
    other_array.forEach(function(v) {this.push(v)}, this);
};

function SearchSplit(searchString) {
    // This will split the searchString at space boundaries
    // while respecting quotes
    words = [];
    var notInsideQuote = true;
    var start =0, end=0;
    searchString = searchString.replace(/^ /g,"");  //remove leading spaces
    for(var i=0; i<searchString.length-1; i++)
    {
        if(searchString.charAt(i)==" " && notInsideQuote)
        {
            words.push(searchString.substring(start,i).trim().replace(/^\"|\"$/g, ""));
            start = i+1;
        }
        else if(searchString.charAt(i)=='"')
            notInsideQuote=!notInsideQuote;
    }
    //todo: should preserve space at end if in the middle of a quote
    word = searchString.substring(start, searchString.length).replace(/^\"|\"$/g, "")
    if (notInsideQuote) {
        words.push(word.trim());
    } else {
        words.push(word);
    }
    //words.push(searchString.substring(start, searchString.length).replace(/^\"|\"$/g, ""));
    return words;

}

function AutoCompleteTerms() {
    var keyWords = ["tenant", "context", "contract", "sip", "dip", "dport", "sport",
                    "prot", "etherT", "arpOpc", "applyToFrag", "tcpRules"];

    this.getMatches = function getMatches(term) {
        var matches = []
        for(var i = 0, l = keyWords.length; i < l; i++) {
            if (keyWords[i].toLowerCase().indexOf(term.toLowerCase()) == 0) {
                matches.push(keyWords[i]);
            }
        }
        return matches;
    }

    this.getTerm = function getTerm(inString) {
        var term = null;
        var candidate = "";
        var lastDelimiter = 0;
        var stringEnd = inString.length
        var previousChar = " ";
        for (var i = 0; i < stringEnd; i++){
            candidate = inString.substring(i, stringEnd);
            for (var h= 0, hl=keyWords.length; h < hl; h++){
                if ((keyWords[h].indexOf(candidate)!=-1) && (previousChar==" ")) {
                    return candidate;
                }
            }
            previousChar = inString[i];
        }
        return null;
    }
}


function connectionSearch(callBack) {
    var margin = {top: 20, right: 10, bottom: 10, left: 10};
    this.width = 100 - margin.left - margin.right;
    var height = 100 - margin.top - margin.bottom;
    var lastSearchString,
        selectedCallBack = callBack;
    var searchTerms = [];
    var onSpaceDone = false;
    var matches = [];
    var validTerms = []; // will track terms that are known to match actual valid terms
    var re_end = new RegExp('([^@=#*]*)$');
    var term = "";
    var container = d3.select("body").select("#autoComplete");
    var enter = container.append("div")
        .attr("id", "ac")
        .attr("class", "ac")
        .append("div")
        .attr("class", "blank-row")
        .append("div")
        .attr("style", "ac-holder");

    container.attr("width", this.width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom);

    var input = enter.append("input")
        .attr("class", "ac-form-control")
        .attr("placeholder", "Search: enter field keyword followed by value")
        .attr("type", "text")
        .attr("spellcheck", "false")
        .on("keyup", onKeyUp);

    var sButton = enter.append("input")
        .attr("type", "button")
        .attr("class", "ac-submit-control")
        .attr("value", "search")
        .on("click", sButtonSelect);

    var searching = enter.append("div").attr("class", "ac-searching")
        .text("");

    var dropDown = enter.append("div").attr("class", "ac-dropdown")
        .style("display", "none");

    function onKeyUp() {
        var searchString = input.node().value.trim().replace(/\s\s+/g, ' ');
        var subSearchString = SearchSplit(searchString).pop();
        var e = d3.event;
        const ASCII_SPACE = 32;
        const ASCII_CR = 13;
        const ASCII_AMP = 38;
        const ASCII_LEFTPAR = 40;
        const ASCII_TAB = 9;
        const ASCII_RIGHT = 39;
        ac = new AutoCompleteTerms();
        //console.log('new search: '+document.getElementById("new_search").value);
        //console.log('key is '+e.which);
        if (!(e.which === ASCII_AMP || e.which === ASCII_RIGHT || e.which === ASCII_CR || e.which === ASCII_SPACE)) {
            // is up/down arrow or enter
            if (!subSearchString || subSearchString === "") {
                showSearching("No results");
                hideDropDown();
                lastSearchString = "";
            } else if (isNewSearchNeeded(subSearchString, lastSearchString)) {
                lastSearchString = subSearchString;
                showSearching();
                term = ac.getTerm(searchString);
                //console.log(terms);
                onSpaceDone = false;  // allow the matched item to be added with a <sp>
                if (term != null) {
                    matches = ac.getMatches(term);
                    showDropDown();

                    processResults(matches, term);
                } else {
                    hideDropDown();
                    hideSearching();
                }
            }

        } else {
            if (e.which === ASCII_SPACE) {
                //console.log('Space');
                //onSpace();
            }
            if (e.which === ASCII_CR) {
                //console.log('Done');
                hideDropDown();
                showSearching("Searching...");
                spinner.spin(target);
                selectedCallBack(input.node().value);
                //searchTerms = [];
            }
            if (e.which === ASCII_RIGHT) {
                //console.log('Right Arrow');
                onRIGHT();
            }
        }

    }

    // this will search for the searchString in the portData
    // array and update the matches array with all the ones
    // that match.
    function showSearching(value) {
        searching.style("display", "block");
        searching.text(value);
    }

    // checks to see if the newTerm has some characters
    // and it is different from the oldTerm
    function isNewSearchNeeded(newTerm, oldTerm) {
        return newTerm.length >= 1 && newTerm != oldTerm;
    }

    function processResults(matches, term) {

        var results = dropDown.selectAll(".ac-row").data(matches.sort(), function (d) {
            return d;
        });
        results.enter()
            .append("div").attr("class", "ac-row")
            .on("click", function (d) {
                row_onClick(d);
            })
            .append("div").attr("class", "ac-title")
            .html(function (d) {
                var re = new RegExp(term, 'i');
                var strPart = d.match(re)[0];

                return d.replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>");

            });

        results.exit().remove();

        //Update results

        results.select(".ac-title")
            .html(function (d, i) {
                var re = new RegExp(term, 'i');
                var strPart = matches[i].match(re);
                var strng = matches[i];
                var offset = 0;
                //console.log(strng);

                if (strPart) {
                    strPart = strPart[0];
                    var response = strng.substring(offset).replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>")+"=";
                    return response;
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
        var selectedTerm = d;
        autoFill(selectedTerm);
    }

    function autoFill(selectedTerm) {
        hideDropDown();
        var inString = input.node().value;
        var lastTermIndex = inString.lastIndexOf(term);

        inString = inString.substring(0,lastTermIndex) + selectedTerm;
        // now need to fix-up the last term
        input.node().value = inString+"=";
        onSpaceDone = true;

    }

    function onRIGHT() {
        if (matches.length > 0) {
            var selectedTerm = matches[0];
            autoFill(selectedTerm);
        }
    }

    function sButtonSelect() {
        //console.log("sButton selected");
        hideDropDown();
        showSearching("Searching...");
        spinner.spin(target);
        selectedCallBack(input.node().value);
        //searchTerms = [];
    }

}


