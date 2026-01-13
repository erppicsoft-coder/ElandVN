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
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'

