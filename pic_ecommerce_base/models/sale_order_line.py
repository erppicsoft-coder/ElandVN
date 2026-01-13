# -*- coding: utf-8 -*-

from odoo import models, api, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ecommerce_line_id = fields.Many2one('pic.ecommerce.order.line', string="Chi tiết đơn hàng E-Commerce")
    ecommerce_price = fields.Float(string="Giá ecommerce")
    free_product_id = fields.Many2one('product.product', "Sản phẩm tặng eCommerce")
    is_reward_line_ecommerce = fields.Boolean("Dòng sản phẩm thưởng eCommerce", default=False)

    # def _confirm_set_combo_program_id(self):
    #     if not self.order_id.ecommerce_id:
    #         return super(SaleOrderLine, self)._confirm_set_combo_program_id()