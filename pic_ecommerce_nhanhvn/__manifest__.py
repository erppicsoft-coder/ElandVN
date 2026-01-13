# -*- coding: utf-8 -*-
{
    'name': "NhanhVN Ecommerce",
    'summary': "Connector",
    'author': "HoanTran",
    'category': 'Ecommerce',
    'version': '1.0',
    'depends': [
        'pic_ecommerce_base',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/ecommerce_order_type_data.xml',
        'views/pic_ecommerce_config_views.xml',
        'views/pic_ecommerce_shop_views.xml',
        'views/pic_ecommerce_order_views.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
}
