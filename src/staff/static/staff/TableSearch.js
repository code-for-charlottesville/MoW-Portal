function searchTable(managementTable, searchBar, extractTextFromRow, getShownVolEmail, emailShownVolsButton){
    /*
    table = dom element to search
    seachBar = input element
    extractTextFromRow = defined elsewhere, function that returns string of text in row to match
    getShownVolEmail = defined elswere, function that returns email from row
    emailShownVolsButton = <a> button with mailto link, is null if the page doesn't support this feature
    */
   
    // no button = no email function
    var emailEnabled = emailShownVolsButton != null
    // set email button to hidden when the emails are being gathered
    // setting button visibility: https://stackoverflow.com/questions/1919432/disabled-the-a-tag-link-by-using-javascript
    if(emailEnabled)
        emailShownVolsButton.style.visibility = 'hidden'
    emails = []
    
    // iterating over rows and cells: https://stackoverflow.com/questions/3065342/how-do-i-iterate-through-table-rows-and-cells-in-javascript
    // performing filtering
    var searchText = searchBar.value.split('&&')
    // '&&' char was requested by client 
    for(let i = 0; i < managementTable.rows.length; i++){
        // looping over by tag name https://stackoverflow.com/questions/23866260/looping-through-javascript-getelementsbytagname-object
        extractedText = extractTextFromRow(managementTable.rows[i]).toLowerCase()
        // checking if the row should be hidden or not
        shouldHide = true
        for(let j = 0; j < searchText.length; j++){
            if(extractedText.indexOf(searchText[j].toLowerCase()) !== -1){
                // one word was found so we shouldn't hide
                shouldHide = false
                break
            }
        }
        // set to hidden or get the email
        if(shouldHide){
            managementTable.rows[i].hidden = true
        } else {
            managementTable.rows[i].hidden = false
            // row is visible
            email = emailEnabled ? getShownVolEmail(managementTable.rows[i]) : ""
            // if the email is not empty and not in the list push it
            if(email != "" && emails.indexOf(email) == -1)
                emails.push(email)
        }
    }

    // emails
    // the emails have been gathered so set the href of the button and make it visible
    // setting button visibility: https://stackoverflow.com/questions/1919432/disabled-the-a-tag-link-by-using-javascript
    if(emailEnabled){
        emailShownVolsButton.href = "mailto:?bcc=" + emails.join(';')
        emailShownVolsButton.style.visibility = 'visible'
    }
}