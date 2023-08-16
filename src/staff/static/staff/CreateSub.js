// readonly https://stackoverflow.com/questions/16298281/set-readonly-property-to-false-for-an-html-text-input-on-clicking-an-anchor-tag
// readonly vs diabled https://stackoverflow.com/questions/1355728/values-of-disabled-inputs-will-not-be-submitted
var job_input = document.getElementById('id_job')
var date_input = document.getElementById('date_input')
var assignment_warning = document.getElementById('assignment-warning')
var a_vol_select = document.getElementById('a_vol_select')
var a_vol_message = document.getElementById('a_vol_message')
var submit = document.getElementById('submit')
var sub_exists_warning = document.getElementById('sub-exists-warning')

async function getAssignmentData(date_value, job_value){
    // see if fields have values
    if(date_value == '' || job_value == ''){
        a_vol_message.hidden = true
        a_vol_select.innerHTML = "<option selected>Please select a date and job first.</option>"
        a_vol_select.setAttribute('readonly', null)
        sub_exists_warning.innerHTML = ""
        assignment_warning.hidden = true
        return
    }
    submit.disabled = true
    // perform the async request
    res = await fetch('/staff/async-parse-assignment/' + date_value + '/' + job_value + '/')
    json = await res.json()
    if(json['status'] == 'error'){
        // something went wrong with the request
        submit.disabled = false
        return
    }
    sub_count = json['sub_count']
    if(sub_count == 0)
        sub_exists_warning.innerHTML = ""
    else if(sub_count == 1)
        sub_exists_warning.innerHTML = "A substitution for this job on this date already exists."
    else
        sub_exists_warning.innerHTML = sub_count + " substitutions already exist for this job on this date."
    // get the volunteers from the response
    vols = json['vols']
    if(vols.length == 0){
        // if there are no volunteers, this combination of date and job must not have had an assignment
        // set warning
        assignment_warning.hidden = false
        a_vol_message.hidden = true
        // set the select back to default
        a_vol_select.innerHTML = "<option selected>Please select a date and job first.</option>"
        a_vol_select.setAttribute('readonly', null)
    } else if(vols.length == 1){
        // get rid of warning
        assignment_warning.hidden = true

        // set the select to readonly and make the only vol selected
        a_vol_select.setAttribute('readonly', true)
        a_vol_message.hidden = true
        vol_name = json['vols'][0]['vol_name']
        vol_pk = json['vols'][0]['vol_pk']
        a_vol_select.innerHTML = "<option selected value=" + vol_pk +">" + vol_name + "</option>"
    } else{
        // get rid of warning
        assignment_warning.hidden = true

        // set the options for select
        options = ""
        vols.forEach((vol)=>{
            // grab the name and pk
            vol_name = vol['vol_name']
            vol_pk = vol['vol_pk']
            selected = vol_pk == "" ? "selected" : ""
            // ^this makes open job the default selection if it is available
            // else it will default to the first option
            options += "<option " + selected + " value=" + vol_pk +">" + vol_name + "</option>"
        })
        // add the options
        // get rid of readonly and make message appear to prompt a selection
        a_vol_select.innerHTML = options
        a_vol_message.hidden = false
        // reminder: need to make a selection here because there are multiple volunteers
        a_vol_select.removeAttribute('readonly')
        // make the box clickable
    }
    submit.disabled = false
}

// add the event listeners to date and job
[job_input, date_input].forEach((item)=>{
    item.addEventListener('change', ()=>{
        getAssignmentData(date_input.value, job_input.value)
    })
})

// need this to pre-populate on error
// if the route and date that are submitted are correct,
// assigned vol needs to populate
window.addEventListener('load', () => {
    getAssignmentData(date_input.value, job_input.value)
});