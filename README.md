# [Meals-on-Wheels](https://portal.cvillemeals.org/) 

## Steps to Run the Project Locally

1. Clone repo - Github: https://github.com/code-for-charlottesville/Meals-on-Wheels-Web-Portal - will need to make sure you have access and SSH set up
2. Install Docker if not installed: https://docs.docker.com/desktop/
3. Make sure you are on the correct branch and cd into the `src` directory
4. Run `make up` - to run dev enviromment
5. The project should be running on http://localhost:8000/

## Background

Meals on Wheels delivers meals to several residents in Charlottesville and Albemarle.  These meals are delivered once a day on weekdays; some residents also receive frozen meals on Fridays to last over the weekend.  There are multiple routes, with an average of 8.5 stops per route.  A typical day will have around 260 deliveries, as some residents will be out of town, or may not get meals on certain days (different people are on different schedules: M-F, M/W/F, etc.).  Meals are prepared at the UVa hospital, delivered to the Meals on Wheels office (at 704 Rose Hill Drive), and from there distributed to the drivers of each route.  Route drivers change on a daily basis.  There are 6 different types of meals; each individual gets one type of meal.  

We currently use a portal (https://portal.cvillemeals.org), developed through a previous offering of this capstone course, which maintains data on customers, volunteers (drivers and otherwise), and staff, as well as managing the route sheets. In January of 2019 the portal could not handle the year change and had many glitches arise, though 2 months later they did fix themselves. We have fine-tuned this portal with pertinent information in order to manage our clients, schedules, and volunteers. Below are the changes that we would like to make to the current portal in addition to the overhaul of the programming.

Customer Management
- Customers: Welcome Screen View to list: address (just street), phone #, route #, diet, and delivery schedule
- Delete place of worship (remove from view)
- Search ability of customers by delivery day – currently search by name, address, and route. We should be able to choose the delivery date and view the name of clients on that date.

Volunteer Management
- Volunteers: Welcome screen view: address, cell phone & home phone, email address, notes, assignments, temporary assignments
- Add function for ability to email volunteers (based off of the overview driver sheet) on any given day, including subs

Reports
- Export Customers: Add delivery day to report
- Billing Report: add a report of client cancellation dates (right now this functionality does not exist and old data disappears and is not stored)


### MOW Contact Information

Joanne Smith, Volunteer Manager
volunteer@cvillemeals.org

Robin Goldstein, Communications Manager
robin@cvillemeals.org
