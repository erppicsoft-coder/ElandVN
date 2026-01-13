# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
	_inherit = 'product.category'

	nhanhvn_id = fields.Integer(string="Nhanhvn Product ID")
	nhanhvn_parent_id = fields.Integer(string="Nhanhvn Product Parent ID")
	nhanhvn_code = fields.Char(string="Nhanhvn Category Code")
	ecommerce_config_id = fields.Many2one('pic.ecommerce.config', string="Sàn thương mại điện tử")