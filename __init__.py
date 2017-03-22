# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .price_list import *
from .product import *

def register():
    Pool.register(
        PriceList,
        Template,
        ListByProduct,
        module='nodux_product_price_list_one', type_='model')
