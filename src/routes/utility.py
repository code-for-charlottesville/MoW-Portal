from models.models import Customer


def remove_customer_from_route(customer):
    """
    :param customer: Customer instance
    sets the customer's route to None, adjusts ordering as needed
    """
    route = customer.route

    if route is None:
        return

    # save old route
    customer.historical_route = str(route)
    # set the route to none
    customer.route = None
    customer.save()


def add_customer_to_route(customer, route):
    """
    :param customer: customer object
    :param route: route object
    customer will get added to the route
    """
    # get old list pre add
    customers_on_route = list(route.get_customer_order())
    # put customer on the route
    customer.route = route
    customer.historical_route = ""
    customer.save()
    # reset the ordering on the route
    customers_on_route.append(customer.pk)
    route.set_customer_order(customers_on_route)
