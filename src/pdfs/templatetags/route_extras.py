import calendar

from django import template

from models.models import Customer, Payment, Route

register = template.Library()


def getRoute(routeId):
    """
        Filter - Given the pk of a route, return the actual route number.
        """
    if routeId is None or Route.objects.get(id=routeId) is None:
        return "No Route Number Found"

    return Route.objects.get(id=routeId)


def getWeekdayString(weekday):
    """
  Filter - Given the integer weekday, return the string representation.
  Note: 0 = Monday, 1 = Tuesday ...
  """
    return calendar.day_name[weekday]


# Source: https://djangosnippets.org/snippets/1357/
def getRangePlusOne(value):
    """
    Filter - returns a list containing range made from given value + 1
    Usage (in template):
    <ul>{% for i in 2|get_range %}
      <li>{{ i }}. Do something</li>
    {% endfor %}</ul>
    Results with the HTML:
    <ul>
      <li>0. Do something</li>
      <li>1. Do something</li>
      <li>2. Do something</li>
    </ul>
    Instead of 3 one may use the variable set in the views
  """
    return range(value + 1)


def getRange(val):
    return range(val)


def getPayment(pk):
    """
  Given a PK/FK to a Payment, return the underlying name field
  """

    if pk is None or Payment.objects.get(id=pk) is None:
        return "No Payment Type Found"

    return Payment.objects.get(id=pk).name


def getCustomer(pk):
    """
  Given a PK/FK to a Customer, return the underlying name field
  """
    if pk is None or Customer.objects.get(id=pk) is None:
        return "No Customer Type Found"

    return Customer.objects.get(id=pk).first_name + \
        " " + Customer.objects.get(id=pk).last_name


def getItem(dictionary, key):
    """
  Allow attributes to be variables for dicts
  """
    return dictionary.get(key)


def numMealsOnDay(cust, date):
    return cust.num_meals_on_day(date)


register.filter("getRoute", getRoute)
register.filter("getRangePlusOne", getRangePlusOne)
register.filter("getWeekdayString", getWeekdayString)
register.filter("getPayment", getPayment)
register.filter("getCustomer", getCustomer)
register.filter("getItem", getItem)
register.filter("numMealsOnDay", numMealsOnDay)
register.filter("getRange", getRange)
