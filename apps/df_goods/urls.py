from django.conf.urls import url
from df_goods.views import IndexView
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
]
