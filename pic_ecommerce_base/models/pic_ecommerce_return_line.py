# -*- coding: utf-8 -*-

from odoo import models, api, fields


class PICEcommerceReturnLine(models.Model):
    _name = 'pic.ecommerce.return.line'

    return_id = fields.Many2one('pic.ecommerce.return')
    item_name = fields.Char(string="Tên sản phẩm")
    item_sku = fields.Char(string="Sku sản phẩm")
    item_id = fields.Integer()
    variation_id = fields.Integer()
    variation_name = fields.Char()
    variation_sku = fields.Char()
    variation_quantity_purchased = fields.Float()
    variation_original_price = fields.Float()
    variation_discounted_price = fields.Float()
    is_wholesale = fields.Boolean()
    weight = fields.Float()
    is_add_on_deal = fields.Boolean()
    is_main_item = fields.Boolean()
    add_on_deal_id = fields.Float()
    group_id = fields.Integer()
    is_set_item = fields.Boolean()
    promotion_type = fields.Char()
    promotion_id = fields.Integer()
    subtotal = fields.Float(string="Doanh thu", compute="_compute_subtotal", store=True)
    product_tmpl_id = fields.Many2one('product.template', string='Sản phẩm')
    code_product = fields.Char(string="Mã nội bộ", related='product_tmpl_id.default_code')

    @api.depends('variation_quantity_purchased', 'variation_discounted_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.variation_quantity_purchased * line.variation_discounted_price
