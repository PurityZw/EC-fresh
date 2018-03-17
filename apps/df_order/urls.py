from django.conf.urls import url
from df_order.views import OrderPlaceView, OrderCommitView

urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'), # 提交订单页面
    url(r'^commit$', OrderCommitView.as_view(), name='commit'), # 创建订单
]
