#! -*- coding: utf8 -*-

#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import *
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.pyson import Id
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from decimal import Decimal
from trytond.wizard import (Wizard, StateView, StateAction, StateTransition,
    Button)
try:
    import bcrypt
except ImportError:
    bcrypt = None
import random
import hashlib
import string
from trytond.config import config

__all__ = ['Template', 'ListByProduct']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    }
DEPENDS = ['active']
DIGITS = 4

class Template:
    __name__ = 'product.template'

    listas_precios = fields.One2Many('product.list_by_product', 'template', 'Listas de precio',
        states=STATES,depends=DEPENDS)

    @fields.depends('cost_price', 'listas_precios', 'id', 'taxes_category',
        'category', 'list_price_with_tax', 'list_price')
    def on_change_list_price(self):
        pool = Pool()

        Product = pool.get('product.product')

        PriceList = pool.get('product.price_list')
        ListByProduct = pool.get('product.list_by_product')
        User = pool.get('res.user')
        priceslist = PriceList.search([('incluir_lista', '=', True)])
        res= {}
        percentage = 0
        precio_final = Decimal(0.0)
        user =  User(Transaction().user)
        precio_total = Decimal(0.0)
        precio_total_iva = Decimal(0.0)
        iva = Decimal(0.0)
        precio_para_venta = Decimal(0.0)

        if self.taxes_category == True:
            if self.category.taxes_parent == True:
                taxes1= self.category.parent.taxes
            else:
                taxes1= self.category.taxes
        else:
            taxes1= self.taxes

        if self.listas_precios:
            pass
        else:
            if self.list_price:
                if priceslist:
                    lineas = []
                    for pricelist in priceslist:
                        percentage = pricelist.percentage/100
                        precio_final = self.list_price * (1 + percentage)

                        if user.company.currency:
                                precio_final = user.company.currency.round(precio_final)
                        if taxes1:
                            if taxes1 == "iva0":
                                rate = Decimal(0.0)
                            elif taxes1 == "no_iva":
                                rate = Decimal(0.0)
                            elif taxes1 == "iva12":
                                rate = Decimal(0.12)
                            elif taxes1 == "iva14":
                                rate = Decimal(0.14)
                            else:
                                rate = Decimal(0.0)

                            iva = precio_final * rate

                        precio_total = precio_final + iva
                        precio_total = user.company.currency.round(precio_total)
                        price_list_lines = ListByProduct()
                        price_list_lines.lista_precio = pricelist.id
                        price_list_lines.fijo = precio_final
                        price_list_lines.fijo_con_iva = precio_total
                        price_list_lines.precio_venta = pricelist.definir_precio_venta

                        lineas.append(price_list_lines)

                        if pricelist.definir_precio_venta == True:
                            precio_para_venta = precio_final
                            precio_total_iva = precio_total
                    self.listas_precios = lineas
                    self.list_price = precio_para_venta
                    self.list_price_with_tax = user.company.currency.round(precio_total_iva)
                else:
                    if taxes1:
                        if taxes1 == "iva0":
                            rate = Decimal(0.0)
                        elif taxes1 == "no_iva":
                            rate = Decimal(0.0)
                        elif taxes1 == "iva12":
                            rate = Decimal(0.12)
                        elif taxes1 == "iva14":
                            rate = Decimal(0.14)
                        else:
                            rate = Decimal(0.0)
                        iva = self.list_price * rate
                    lineas = []
                    self.listas_precios = lineas
                    self.list_price = self.list_price
                    self.list_price_with_tax = user.company.currency.round(self.list_price + iva)

    @fields.depends('listas_precios', 'list_price', 'taxes_category', 'category',
        'list_price_with_tax', 'customer_taxes', 'cost_price')
    def on_change_listas_precios(self):
        if self.list_price_with_tax:
            price_with_tax = self.list_price_with_tax
        else:
            price_with_tax = Decimal(0.0)

        self.list_price_with_tax = price_with_tax
        self.list_price = self.list_price

        if self.listas_precios:
            for lista in self.listas_precios:
                if (lista.fijo_con_iva > Decimal(0.0)) and  (lista.precio_venta == True):
                    self.list_price_with_tax = lista.fijo_con_iva
                    self.list_price = lista.fijo

    @classmethod
    def validate(cls, products):
        for product in products:
            name_list = []
            for lists in product.listas_precios:
                if lists.lista_precio.name in name_list:
                    product.raise_user_error('%s se encuentra duplicada', lists.lista_precio.name)
                else:
                    name_list.append(lists.lista_precio.name)
                    super(Template, cls).validate(products)


class ListByProduct(ModelSQL, ModelView):
    "List By Product"
    __name__ = "product.list_by_product"

    template = fields.Many2One('product.template', 'Product Template',
        required=True, ondelete='CASCADE', select=True, states=STATES,
        depends=DEPENDS)
    lista_precio = fields.Many2One('product.price_list', 'Lista de Precio',
        required=True, ondelete='CASCADE', select=True, states=STATES,
        depends=DEPENDS)
    fijo = fields.Numeric('Precio sin IVA', digits=(16, 6))
    precio_venta = fields.Boolean('Definir como precio de VENTA')
    product = fields.Many2One('product.product', 'Product Template')
    fijo_con_iva = fields.Numeric('Precio con IVA', digits=(16, 6))

    @classmethod
    def __setup__(cls):
        super(ListByProduct, cls).__setup__()

    def get_rec_name(self, lista_precio):
        return self.lista_precio.name

    @classmethod
    def search_rec_name(cls, lista_precio, clause):
        return [('lista_precio',) + tuple(clause[1:])]

    @fields.depends('_parent_template.cost_price', 'lista_precio', 'fijo',
        '_parent_template.taxes_category', '_parent_template.category',
        '_parent_template.id', '_parent_template.list_price')
    def on_change_lista_precio(self):
        pool = Pool()
        percentage = 0
        precio_final = Decimal(0.0)
        use_new_formula = False

        if self.lista_precio:
            if self.lista_precio.lines:
                for line in self.lista_precio.lines:
                    if line.percentage > 0:
                        percentage = line.percentage/100

            if self.template.taxes_category == True:
                if self.template.category.taxes_parent == True:
                    taxes1= self.template.category.parent.taxes
                else:
                    taxes1= self.template.category.taxes
            else:
                taxes1= self.template.taxes

            if self.template.cost_price:
                precio_final = self.template.cost_price * (1 + percentage)

            if taxes1:
                if taxes1 == "iva0":
                    rate = Decimal(0.0)
                elif taxes1 == "no_iva":
                    rate = Decimal(0.0)
                elif taxes1 == "iva12":
                    rate = Decimal(0.12)
                elif taxes1 == "iva14":
                    rate = Decimal(0.14)
                else:
                    rate = Decimal(0.0)
                iva =precio_final * rate

            precio_total = precio_final + iva

            self.fijo = Decimal(str(round(precio_final, 6)))
            self.fijo_con_iva = Decimal(str(round(precio_total, 6)))

    @fields.depends('_parent_template.cost_price', 'lista_precio', 'fijo',
        '_parent_template.taxes_category', '_parent_template.category',
        '_parent_template.id', 'fijo_con_iva', '_parent_template.list_price')
    def on_change_fijo_con_iva(self):
        pool = Pool()
        precio_total = self.fijo
        iva = Decimal(0.0)
        if self.fijo_con_iva:

            if self.template.taxes_category == True:
                if self.template.category.taxes_parent == True:
                    taxes1= self.template.category.parent.taxes
                else:
                    taxes1= self.template.category.taxes
            else:
                taxes1= self.template.taxes

            if taxes1:
                if taxes1 == "iva0":
                    iva = Decimal(0.0)
                elif taxes1 == "no_iva":
                    iva = Decimal(0.0)
                elif taxes1 == "iva12":
                    iva = Decimal(0.12)
                elif taxes1 == "iva14":
                    iva = Decimal(0.14)
                else:
                    iva = Decimal(0.0)

            precio_total = self.fijo_con_iva /(1+iva)
            self.fijo =  Decimal(str(round(precio_total, 6)))


    @fields.depends('_parent_template.cost_price', 'lista_precio', 'fijo',
        '_parent_template.taxes_category', '_parent_template.category',
        '_parent_template.id', 'fijo_con_iva', '_parent_template.list_price')
    def on_change_fijo(self):
        pool = Pool()
        precio_total_iva = self.fijo_con_iva
        iva = Decimal(0.0)

        if self.fijo_con_iva:
            if self.template.taxes_category == True:
                if self.template.category.taxes_parent == True:
                    taxes1= self.template.category.parent.taxes
                else:
                    taxes1= self.template.category.taxes
            else:
                taxes1= self.template.taxes

            if taxes1:
                if taxes1 == "iva0":
                    iva = Decimal(0.0)
                elif taxes1 == "no_iva":
                    iva = Decimal(0.0)
                elif taxes1 == "iva12":
                    iva = Decimal(0.12)
                elif taxes1 == "iva14":
                    iva = Decimal(0.14)
                else:
                    iva = Decimal(0.0)

            precio_total_con_iva = self.fijo*(1+iva)
            self.fijo_con_iva = Decimal(str(round(precio_total_con_iva, 6)))


    @fields.depends('_parent_template.list_price', '_parent_template.id', 'fijo', 'precio_venta')
    def on_change_precio_venta(self):
        self.list_price = self.fijo
        self.template.list_price =  self.list_price
