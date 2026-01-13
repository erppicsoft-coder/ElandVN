# -*- coding: utf-8 -*-
#
#    PIC Technology Solution Co.,Ltd.
#
#    Copyright (C) 2024-TODAY PIC Technology Solution(<https://www.picsolution.com.vn>)
#    Author: CuongPham (phamcuong3004@gmai.com)
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE
#

from odoo import models, api, fields
from .nhanhvn_constants import (
    NHANHVN_ORDER_STATUS,
)


class PICEcommerceOrderState(models.Model):
    _inherit = 'pic.ecommerce.order.state'

    nhanhvn_order_status = fields.Selection(NHANHVN_ORDER_STATUS, string="Trạng thái đơn hàng")