var extractTextFromRow = (row)=>{
    /*
    row = <tr> to extract text from
    */
    // iterating over rows and cells https://stackoverflow.com/questions/3065342/how-do-i-iterate-through-table-rows-and-cells-in-javascript
    // looping over by tag name https://stackoverflow.com/questions/23866260/looping-through-javascript-getelementsbytagname-object
    columnsInRow = row.getElementsByTagName('td')
    textInRow = ""
    for(let i = 0; i < columnsInRow.length - 1; i++){
        // delete button is the last column so exclude it
        textInRow += ' ' + columnsInRow[i].getElementsByTagName('a')[0].innerHTML.toLowerCase().trim() + ' '
    }
    // escaping html using textarea: https://stackoverflow.com/questions/7394748/whats-the-right-way-to-decode-a-string-that-has-special-html-entities-in-it
    decodedArea = document.createElement('textarea')
    decodedArea.innerHTML = textInRow
    return decodedArea.value
}

// setting up the emails
emailShownVolsButton = document.getElementById('email-shown-vols-button')
if(emailShownVolsButton == null)
    getShownVolEmail = null
// else, defined elswhere

// declaring vars for searchTable
var searchBar = document.getElementById('search')
var managementTable = document.getElementById('managementTable').tBodies[0]

// call the searchTable function so that the button can be populated
searchTable(managementTable, searchBar, extractTextFromRow, getShownVolEmail, emailShownVolsButton)

// adding event listener for keyup
searchBar.addEventListener('keyup', ()=>{
    // still take up space https://stackoverflow.com/questions/6393632/jquery-hide-element-while-preserving-its-space-in-page-layout
    if(searchBar.value != '')
        document.getElementById('multiple-filter-note').style.visibility = 'visible'
    else
        document.getElementById('multiple-filter-note').style.visibility = 'hidden'
    // getShownVolEmail defined on pages where this function is needed
    searchTable(managementTable, searchBar, extractTextFromRow, getShownVolEmail, emailShownVolsButton)
})
