# -*- coding: utf-8 -*-

from odoo import models, api, fields, _


class PICEcommerceShop(models.Model):
    _name = 'pic.ecommerce.shop'
    _description = 'Shop TMĐT'

    name = fields.Char(string="Shop")
    shop_id = fields.Char(string="Shop ID")
    app_id = fields.Integer(string="App ID")
    type = fields.Selection([
        ('shopee', 'Shopee'),
        ('lazada', 'Lazada'),
        ('tiktok', 'TikTok'),
        ('tiki', 'TiKi'),
        ('sendo', 'Sen đỏ')], string="Sàn TMĐT")
    ecommerce_config_id = fields.Many2one('pic.ecommerce.config', string="Sàn TMĐT")
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    partner_shipping_id = fields.Many2one('res.partner', string="Địa địa chỉ giao hàng")
    partner_invoice_id = fields.Many2one('res.partner', string="Địa chỉ xuất hóa đơn")
    expired_at = fields.Datetime(string="Ngày hết hạn")
    active = fields.Boolean(string="Hiệu lực", default=True)
