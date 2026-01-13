# -*- coding: utf-8 -*-

from odoo import models, api, fields


class PICEcommerceReturn(models.Model):
    _name = 'pic.ecommerce.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_time DESC"

    name = fields.Char('Trả hàng số')
    create_time = fields.Datetime('Ngày tạo trả hàng')
    update_time = fields.Datetime('Ngày cập nhật')
    due_date = fields.Datetime('Ngày đến hạn')
    return_seller_due_date = fields.Integer()
    return_ship_due_date = fields.Integer()
    amount_before_discount = fields.Float('Tiền trước chiết khấu')
    tracking_number = fields.Char('Mã điều vận')
    refund_amount = fields.Float('Số tiền hoàn')
    reason = fields.Char('Lý do')
    text_reason = fields.Char('Diễn giải')
    needs_logistics = fields.Boolean('Điều vận')
    status = fields.Char('Trạng thái trả hàng')
    user_name = fields.Char('Người mua')
    email = fields.Char('Email người mua')
    ordersn = fields.Char('Tham chiếu')
    ecommerce_id = fields.Many2one('pic.ecommerce.order', string='E-Commerce số')
    session_id = fields.Many2one('pic.ecommerce.session', string="Phiên đồng bộ")
    config_id = fields.Many2one('pic.ecommerce.config', string="Nguồn e-commerce", related="session_id.config_id")
    user_id = fields.Many2one('res.users', 'Người chịu trách nhiệm')
    last_sale_id = fields.Many2one('sale.order', 'Đơn hàng pic')
    state = fields.Selection([('draft', 'Dự thảo'), ('confirm', 'Xác nhận'), ('done', 'Hoàn thành'),
         ('cancel', 'Hủy')], default="draft", string="Trạng thái")
    line_ids = fields.One2many('pic.ecommerce.return.line', 'return_id')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
