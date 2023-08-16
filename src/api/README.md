# API
- The API uses Django Rest Framework to add REST functionality to existing Django models
- the API is on revision v1, so all api routes must be proceeded by /api/v1/<api-url-here> (05/18/2022)
Example: /api/v1/announcements
- All routes except for login require authorization headers
Authorization | Token <randomauthtoken>

### Login
(from dj_rest_auth.urls)

accepts a username and password from the body and returns a Token to be used for authorization

url: dj-rest-auth/login/
- Body: {"username": string, "password": string}
- POST

return object: {
    "key": string
}

### Announcements
(api.views.ListAnnouncement)

returns a list of all announcements

url: announcements/

- no query parameters
- GET

return object: [
    {
        "id": int,
        "created_by": string,
        "displayUntil": string (date YYYY-mm-dd),
        "created": string (date YYYY-mm-dd),
        "announcement":  string
    }
]

Django Models: ManagerAnnouncements

### Delivery Feedback
(api.deliveryFeedback.deliveryFeedbackView.deliveryFeedbackViewSet)

url: delivery-feedback/?route=<int:routeId>&run_date=<string:run_date>&customer=<int:customer_id>

- query parameters: routeId(required), run_date, customer 
- GET, PUT

return object: {

    "delivery_status": string,
    "customer_status": string,
    "notes": string
}

url: missing-delivery-feedback-today/<int:routeId>

The missing-delivery-feedback-today endpoint must be called each day before feedback can be submitted.

- query parameter: routeId (Ex. /api/v1/missing-delivery-feedback-today/4)
- GET

return object: [
    {
        "customer": int,
        "feedback_provided": boolean
    }
]

Django Model: Run

### Route Overview
(api.views.RouteOverview)

url: route-overview/<int:routeId>/date/<str:input_date>

- query parameters: routeId, input_date (Ex. /api/v1/route-overview/2/date/2022-06-05)
- GET

return object: [
    {
        "name": ,
        "number": ,
        "description": ,
        customers: []
    }
]

Django Model: Route

### My Jobs
(api.myJobs.myJobsView.MyJobsViewSet)

returns all upcoming jobs and substitutions for a user that are no later than the fifth in the future.

url: my-jobs/
- no query parameters
- GET

return object: [
    {
        "routeNumber": string,
        "jobId": int,
        "jobName": string,
        "jobType": string,
        "volunteerId": int,
        "date_yyyy_mm_dd": string (date YYYY-mm-dd),
        "isSub": boolean
    }
]

Django Models: Assignment, Substitution

## Testing
Testing can be done by running ./manage.py test api inside the running web container