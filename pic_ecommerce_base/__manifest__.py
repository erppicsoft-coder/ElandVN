# -*- coding: utf-8 -*-
#############################################################################
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
#############################################################################
{
    'name': 'Thương mại điện tử',
    'version': '17.0.1.0.4',
    'category': 'Sales',
    'summary': """Thương mại điện tử""",
    'author': 'PIC Technology Solution',
    'company': 'PIC Technology Solution',
    'maintainer': 'PIC Technology Solution',
    'website': "https://www.picsolution.com.vn",
    'depends': [
        'sale_management',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/pic_ecommerce_order_view.xml',
        'views/pic_ecommerce_session_view.xml',
        'views/pic_ecommerce_view.xml',
        'views/pic_ecommerce_config_view.xml',
        'views/pic_ecommerce_return_view.xml',
        'views/pic_ecommerce_payment_view.xml',
        'views/pic_ecommerce_order_state_view.xml',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
