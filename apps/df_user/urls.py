from django.conf.urls import url
from df_user.views import RegisterView, ActiveView, LoginView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='user'),  # 用户注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户激活
    url(r'^login$', LoginView.as_view(), name='login'),
]
