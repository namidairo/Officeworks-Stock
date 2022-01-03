import click
import requests
from datetime import timedelta
from requests_cache import CachedSession

allStoresUrl = "https://www.officeworks.com.au/contact-us?view=stores&format=json"
productSearchUrl = "https://www.officeworks.com.au/shop/ProductSearchView?pageSize=50&langId=-1&catalogId=-1&storeId=10151&searchTerm="
availabilityUrl = "https://api.officeworks.com.au/v2/availability/store"

# Cache for larger requests
session = CachedSession(
    'officeworks',
    cache_control=False,
    expire_after=timedelta(days=7)
)

@click.command()
@click.option('--state', default='all', type=click.Choice(['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'all'], case_sensitive=False))
@click.option('--productid', help='Product to search for', prompt=True)
@click.option('--skiplookup/--no-skiplookup', is_flag=True, default=False, help='Skip lookup, useful for items delisted')
def main(state, productid, skiplookup):
    click.echo("Searching for product code: {} in {}".format(productid, state))

    # Get product description
    if skiplookup:
        click.echo("Skipping lookup")
    else:
        productDescription = requests.get(productSearchUrl + productid).json()
        if len(productDescription['products']) == 0:
            click.echo("No product found. Have you entered the correct product code? Alternatively, use --skiplookup for delisted items")
            return

        # Get product name
        for product in productDescription["products"]:
            if productid == product["identity"]["partNumber"]:
                productName = product["identity"]["name"]
                break

        try:
            click.echo("Product: {}".format(productName))
        except NameError:
            click.echo("Error finding product name")
            return    

    # Get all stores. Cached for 1 week, since it's a large request.
    click.echo("Getting all stores")
    allStores = session.get(allStoresUrl).json()

    try:
        if(len(allStores['stores']) == 0):
            click.echo("Empty store list")
            return
    except KeyError:
        click.echo("Invalid store list")
        return

    # Filter by state
    filteredStores = list()
    if state != 'all':
        for store in allStores["stores"]:
            if store['address']['storeState'] == state:
                filteredStores.append(store)
    else:
        filteredStores = allStores["stores"]

    click.echo("Checking {} stores".format(len(filteredStores)))
    
    # Get availability for each store
    for store in filteredStores:
        storeId = store["storeId"]
        storeAvailabilityUrl = "{}/{}?partNumber={}".format(availabilityUrl, storeId, productid)
        availability = requests.get(storeAvailabilityUrl).json()
        try:
            if("options" in availability[0]):
                for option in availability[0]["options"]:
                    if(option["qty"] > 0 and option['type'] == "inStore"):
                        if(state != 'all'):
                            click.echo("Found: {} at {}".format(option['qty'], store['storeName']))
                        else:
                            click.echo("Found: {} at {} ({})".format(option['qty'], store['storeName'], store['address']['storeState']))
        except:
            click.echo("Error getting availability for {}".format(store["storeName"]))

if __name__ == "__main__":
    main()