# -*- coding: utf-8 -*-

from odoo import models, api, fields


class PICEcommerceOrderState(models.Model):
    _name = 'pic.ecommerce.order.state'
    _description = 'Toàn trình đơn hàng'
    _order = 'update_time desc'

    ecommerce_id = fields.Many2one('pic.ecommerce.order', string='Đơn hàng TMĐT', ondelete='cascade')
    name = fields.Char(string="Mô tả")
    update_time = fields.Datetime(string="Thời gian")

    order_status = fields.Selection([
        ('UNPAID', 'Chờ thanh toán'),
        ('TO_PACK', 'Chờ lấy hàng'), ('TO_SHIP', 'Chờ đóng gói'), ('READY_TO_SHIP', 'Chờ bàn giao'),
        ('PROCESSED', 'Đang giao'), ('RETRY_SHIP', 'Giao lại'), ('SHIPPED', 'Đã giao'),
        ('TO_CONFIRM_RECEIVE', 'Chờ xác nhận nhận hàng'), ('COMPLETED', 'Hoàn thành'),
        ('INVOICE_PENDING', 'Chờ hóa đơn'), ('INCIDENT', 'Sự cố'),
        ('IN_CANCEL', 'Chờ hủy'), ('CANCELLED', 'Đã hủy'),
        ('TO_RETURN', 'Chờ thu hồi'), ('RETURNED', 'Đã thu hồi'),
    ], string="Trạng thái sàn")

    response_data = fields.Text(
        string="Dữ liệu phản hồi",
        help="JSON response từ API/Webhook"
    )
    source = fields.Selection([
        ('api', 'API'),
        ('webhook', 'Webhook')
    ], string="Nguồn cập nhật", default='api')