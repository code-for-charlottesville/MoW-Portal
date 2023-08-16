var extractTextFromRow = (row)=>{
    /*
    row = <tr> to extract text from
    */
    // iterating over rows and cells: https://stackoverflow.com/questions/3065342/how-do-i-iterate-through-table-rows-and-cells-in-javascript
    // looping over by tag name https://stackoverflow.com/questions/23866260/looping-through-javascript-getelementsbytagname-object
    columnsInRow = row.getElementsByTagName('td')
    textInRow = ""
    for(let i = 0; i < columnsInRow.length; i++){
        if(i == 0 || i == 1){
            // first two cols are in first a tag
            textInRow += ' ' + columnsInRow[i].getElementsByTagName('a')[0].innerHTML.toLowerCase().trim() + ' '
        } else{
            // multiple a tags for rest of cols
            for(let j = 0; j < columnsInRow[i].getElementsByTagName('a').length; j++)
                textInRow += ' ' + columnsInRow[i].getElementsByTagName('a')[j].innerHTML.toLowerCase().trim() + ' '
        }
    }
    // escaping html using textarea: https://stackoverflow.com/questions/7394748/whats-the-right-way-to-decode-a-string-that-has-special-html-entities-in-it
    decodedArea = document.createElement('textarea')
    decodedArea.innerHTML = textInRow
    return decodedArea.value
}

// defind how to get the ShownVolEmails out of a particular row
var getShownVolEmail = (row) =>{
    /*
    row = <tr> to extract email from
    */
    // looping over by tag name https://stackoverflow.com/questions/23866260/looping-through-javascript-getelementsbytagname-object
    // email can be the only span defined
    emailSpan = row.getElementsByTagName('td')[0].getElementsByTagName('a')[1]
    return emailSpan.innerHTML.trim()
}

// async function to load the table
async function setTableHtml(url){
    /*
    url = url to make request to
    */
    // make request
    htmlResponse = await fetch(url)
    htmlResponse = await htmlResponse.text()

    // set the html
    document.getElementById("assignments").innerHTML = htmlResponse
    document.getElementById("filterDiv").hidden = false

    // prepare the searching function
    var searchBar = document.getElementById('search')
    var managementTable = document.getElementById('managementTable').tBodies[0]
    var emailShownVolsButton = document.getElementById('email-shown-vols-button')

    // call the searchTable function on load so that the email button can have an accurate link
    searchTable(managementTable, searchBar, extractTextFromRow, getShownVolEmail, emailShownVolsButton)

    // adding event listener for keyup
    searchBar.addEventListener('keyup', ()=>{
        // still take up space https://stackoverflow.com/questions/6393632/jquery-hide-element-while-preserving-its-space-in-page-layout
        if(searchBar.value != '')
            document.getElementById('multiple-filter-note').style.visibility = 'visible'
        else
            document.getElementById('multiple-filter-note').style.visibility = 'hidden'
        searchTable(managementTable, searchBar, extractTextFromRow, getShownVolEmail, emailShownVolsButton)
    })
}

// request_url defined in template
setTableHtml(request_url);
var periods = ''
setInterval(()=>{
    periods += '.'
    span = document.getElementById('periods')
    if(span != null)
        span.innerHTML = periods
}, 750)