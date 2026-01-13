# -*- coding: utf-8 -*-

from odoo import models, api, fields, _


class PICEcommerceOrderType(models.Model):
	_name = 'pic.ecommerce.order.type'
	_description = 'Loại đơn hàng'

	name = fields.Char(string="Loại đơn hàng")
	code = fields.Integer(string="Mã")
	active = fields.Boolean(string="Hiệu lực", default=True)