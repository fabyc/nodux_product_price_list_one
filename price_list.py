# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal

from sql import Null
from sql.conditionals import Case
from simpleeval import simple_eval

from trytond.model import ModelView, ModelSQL, MatchMixin, fields
from trytond.tools import decistmt
from trytond.pyson import If, Eval
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond import backend

__all__ = ['PriceList']


class PriceList(ModelSQL, ModelView):
    'Price List'
    __name__ = 'product.price_list'

    name = fields.Char('Name', required=True, translate=True)
    company = fields.Many2One('company.company', 'Company', required=True,
        select=True, domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ])
    tax_included = fields.Boolean('Tax Included')
    percentage = fields.Numeric('Porcentaje de descuento')
    formula = fields.Char('Formula', required=True,
        help=('Python expression that will be evaluated with:\n'
            '- unit_price: the original unit_price'))
    incluir_lista = fields.Boolean('Incluir lista de precio en producto', states={
        'readonly': (Eval('definir_precio_venta', True))
    })

    definir_precio_venta = fields.Boolean('Definir como precio de venta', help="Definir como precio de venta principal")

    @classmethod
    def __setup__(cls):
        super(PriceList, cls).__setup__()
        cls.formula.states['readonly'] = Eval('active', True)

    @fields.depends('percentage', 'formula')
    def on_change_percentage(self):
        if self.percentage:
            if self.percentage > 0:
                percentage = self.percentage/100
                p = str(percentage)
            formula = 'unit_price * (1 + ' +p+')'
            self.formula = formula

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_tax_included():
        return False

    def get_context_formula(self, product, unit_price, quantity, uom):
        return {
            'names': {
                'unit_price': unit_price,
                },
            }

    def compute(self, product, unit_price, quantity, uom,
            pattern=None):
        'Compute price based on price list of party'

        def get_unit_price(**context):
            'Return unit price (as Decimal)'
            context.setdefault('functions', {})['Decimal'] = Decimal
            return simple_eval(decistmt(self.formula), **context)
        Uom = Pool().get('product.uom')

        if pattern is None:
            pattern = {}

        pattern = pattern.copy()
        pattern['product'] = product and product.id or None
        pattern['quantity'] = Uom.compute_qty(uom, quantity,
            product.default_uom, round=False) if product else quantity

        context = self.get_context_formula(
            product, unit_price, quantity, uom)
        return get_unit_price(**context)
        #return unit_price
