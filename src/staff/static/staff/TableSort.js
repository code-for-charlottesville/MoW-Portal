function sortRows(tableName, column, dir, colIndex){
    /*
    column = which column to sort, do not manipulate
    dir = 1 for sort ascending alphabetically by last name
    dir = -1 for sort descending alphabetically by last name
    colIndex = which column the names are in, do not manipulate
    */
    managementTable = document.getElementById(tableName).tBodies[0]
    dir = Number(dir)
    // create array from the table elements and set at end
    // https://stackoverflow.com/questions/55462632/javascript-sort-table-column-on-click
    items = Array.from(managementTable.rows);
    items.sort((self, otherRow)=>{
        // looping over by tag name https://stackoverflow.com/questions/23866260/looping-through-javascript-getelementsbytagname-object
        self = self.getElementsByTagName("td")[colIndex]
        otherRow = otherRow.getElementsByTagName("td")[colIndex]
        // the first a tag is typically the value
        selfName = self.getElementsByTagName("a")[0].innerHTML.toLowerCase()
        otherRowName = otherRow.getElementsByTagName("a")[0].innerHTML.toLowerCase()
        if(column == 'jobs' || column == 'routes'){
            selfRouteNumber = Number(self.getElementsByTagName("span")[0].innerHTML)
            otherRouteNumber = Number(otherRow.getElementsByTagName("span")[0].innerHTML)
            if(selfRouteNumber != -1 && otherRouteNumber != -1){
                // compare the route numbers
                return dir*(selfRouteNumber - otherRouteNumber)
            } else if(selfRouteNumber != -1){
                // routes always get priority to preserve legacy layout
                return -1*dir
            } else if(otherRouteNumber != -1){
                // routes always get priority to preserve legacy layout
                return dir
            }
        } else if(column.includes('dates')){
            // https://stackoverflow.com/questions/14781153/how-to-compare-two-string-dates-in-javascript
            // get the date number out
            selfName = selfName.split(',')[1].trim()
            otherRowName = otherRowName.split(',')[1].trim()
            res = Date.parse(selfName) < Date.parse(otherRowName)
            if(res){
                res = 1
            } else{
                res = -1
            }
            return res*dir
        } else if(column.includes("last_job")){

            if (selfName == "none"){
                selfName = "Jan 1, 1000"
            }
            if (otherRowName == "none"){
                otherRowName = "Jan 1, 1000"
            }
            res = Date.parse(selfName) < Date.parse(otherRowName)
            if(res){
                res = 1
            } else{
                res = -1
            }
            return res*dir
        }
        // sort alphabetically
        return dir*(selfName.localeCompare(otherRowName))
    })
    // reset onclick
    dir = dir*-1
    document.getElementById(column).setAttribute("onclick", "sortRows('" + tableName + "', '" + column + "', " + dir + ", " + colIndex + ")")

    // set the rows in the table
    // create array from the table elements and set at end
    // https://stackoverflow.com/questions/55462632/javascript-sort-table-column-on-click
    managementTable.innerHTML = ''
    items.forEach((item)=>{
        managementTable.appendChild(item)
    })
}